"""TGJU tools: symbol search and browsing, live prices, category tables, daily history, key-rate summary."""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Any, Literal

from pydantic import Field

from .http import API, CALL, ApiError, fetch
from .registry import tool

# Symbols the site quotes in Rial. Heuristic on the symbol name (the feed carries no unit): gold grams,
# coins, free-market currencies and Bitcoin/Ethereum in IRR. Everything else keeps its listed unit.
_RIAL = re.compile(
    r"^(geram\d+|gold_\d+k|sekee|sekeb|nim|rob|gerami|retail_\w+|mesghal|abshodeh|tgju_gold_\w+|silver_\d+|"
    r"price_dollar_(rl|dt|sm|ex|soleymani)|price_[a-z]{3}|crypto-[\w-]+-irr)$"
)
_NOT_RIAL = re.compile(r"blubber|ratio|_buy$|_down$|_real$")

CATEGORIES = {
    "gold": ("91818", "rial"),
    "coin": ("28068", "rial"),
    "coin_retail": ("28067", "rial"),
    "currency": ("28070", "rial"),
    "currency_government": ("28071", "rial"),
    "currency_sana": ("28072", "rial"),
    "currency_nima": ("31741", "rial"),
    "crypto": ("28426", "usd"),
}

# (label, symbol) shown by tj_market_summary
KEY_RATES = [
    ("dollar", "price_dollar_rl"),
    ("euro", "price_eur"),
    ("dirham", "price_aed"),
    ("pound", "price_gbp"),
    ("lira", "price_try"),
    ("gold_18k_gram", "geram18"),
    ("gold_24k_gram", "geram24"),
    ("gold_mesghal", "mesghal"),
    ("coin_emami", "sekee"),
    ("coin_bahar_azadi", "sekeb"),
    ("coin_half", "nim"),
    ("coin_quarter", "rob"),
    ("coin_gerami", "gerami"),
    ("gold_ounce", "ons"),
    ("silver_ounce", "silver"),
    ("brent_oil", "oil_brent"),
    ("bitcoin_usd", "crypto-bitcoin"),
    ("bitcoin_irr", "crypto-bitcoin-irr"),
    ("ethereum_usd", "crypto-ethereum"),
    ("tether", "crypto-tether-irr"),
]


def _num(v: Any) -> int | float | None:
    """'2,638,000' or '<span>0.38%</span>' -> number; '-' or junk -> None."""
    s = re.sub(r"<[^>]+>|[,%\s]", "", str(v))
    try:
        f = float(s)
    except ValueError:
        return None
    return int(f) if f.is_integer() else f


def _unit(symbol: str, default: str | None = None) -> str:
    if default:
        return default
    return "rial" if _RIAL.match(symbol) and not _NOT_RIAL.search(symbol) else "as_listed"


def _toman(v: int | float | None) -> int | float | None:
    return None if v is None else _num(f"{v / 10:.1f}")


def _money(row: dict[str, Any], unit: str, *fields: str) -> dict[str, Any]:
    """Add `<field>_toman` next to rial fields."""
    if unit == "rial":
        for f in fields:
            row[f + "_toman"] = _toman(row.get(f))
    return row


_MONTHS = "فروردین اردیبهشت خرداد تیر مرداد شهریور مهر آبان آذر دی بهمن اسفند".split()
_STALE_DAYS = 2


def _now() -> datetime:
    return datetime.now(timezone(timedelta(hours=3, minutes=30)))  # Tehran, no DST


def _jalali_day(d: date) -> int:
    """Day of the Jalali year (1-366) of a Gregorian date."""
    return (d - date(d.year if (d.month, d.day) >= (3, 21) else d.year - 1, 3, 21)).days + 1


def _stale(t: str | None) -> bool:
    """Quote older than 2 days. `t`: '2026-10-17 00:00:00' / '2026/10/17' (feed, history) or a table cell,
    'HH:MM:SS' (today) or '۲۷ مهر' (older)."""
    today = _now().date()
    if m := re.match(r"(\d{4})[-/](\d\d)[-/](\d\d)", t or ""):
        return (today - date(*map(int, m.groups()))).days > _STALE_DAYS
    m = re.fullmatch(r"(\d+) (\S+)", (t or "").translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")).strip())
    if m and m[2] in _MONTHS:
        month = _MONTHS.index(m[2])
        # shortcut: fixed month lengths (31 x6, 30 x6) and Nowruz = 21 March, so +-1 day; fine for a 2-day test.
        ordinal = month * 31 - max(month - 6, 0) + int(m[1])
        return (_jalali_day(today) - ordinal) % 365 > _STALE_DAYS
    return False


def _cells(row: list[str]) -> list[int | float | None]:
    return [_num(c) for c in row]


def _signed(cell: str, v: int | float | None) -> int | float | None:
    """The site marks a fall with CSS class 'low' on the change cells."""
    return -v if v is not None and 'class="low"' in cell else v


@tool("Search symbols")
async def tj_search_symbols(
    query: Annotated[
        str, Field(min_length=2, description="Name or code, Persian or English, e.g. 'سکه امامی', 'bitcoin', 'brent'.")
    ],
    scope: Annotated[
        Literal["internal", "global", "crypto"],
        Field(
            description="internal = Iranian markets (gold, coins, currencies, funds), global = world markets and pairs, crypto = coins."
        ),
    ] = "internal",
    limit: Annotated[int, Field(ge=1, le=10, description="Max matches (the site returns at most 10).")] = 10,
) -> dict[str, Any]:
    """Find TGJU symbols by name.

    Use when you do not know the symbol slug; pass a result's `symbol` to tj_get_prices or tj_price_history.
    Main symbols come back as their short live symbol; the rest as a slug, which tj_get_prices answers from
    the latest daily history row (`source: history`).
    """
    body = await fetch(f"{API}/v1/search", {"q": query})
    raw = body["response"]["result"].get(
        {"internal": "markets.internal", "global": "markets.global", "crypto": "crypto"}[scope]
    )
    hits = (json.loads(raw) if isinstance(raw, str) else raw or {}).get("hits", {})
    live = await _live()
    out = []
    for h in hits.get("hits", [])[:limit]:
        s = h["_source"]
        grade = s.get("grade") or ""
        # 'grade' is the short symbol (sekee) only when the live feed has it; exchange quotes share one grade
        # ('irec-sell') and fail in history. The slug in s1 always works in tj_price_history and tj_get_prices.
        symbol = grade if scope == "internal" and grade in live else s.get("s1")
        out.append(
            {
                "symbol": symbol,
                "title": s.get("title"),
                "title_en": s.get("title_en"),
                "group": s.get("category"),
                "slug": s.get("s1"),
            }
        )
    return {"total": hits.get("total", {}).get("value", 0), "matches": out}


@tool("Browse categories")
async def tj_list_categories(
    parent_id: Annotated[
        str | None,
        Field(description="Folder id to open, e.g. '28064' (gold market) or 'currencies'. Omit for the top level."),
    ] = None,
    limit: Annotated[int, Field(ge=1, le=100, description="Max items.")] = 50,
    offset: Annotated[int, Field(ge=0, description="Items to skip (big folders such as crypto have thousands).")] = 0,
) -> dict[str, Any]:
    """Browse TGJU's market tree: folders (with ids) and symbols.

    Use to discover a group; call tj_category_table with a folder id to get its prices, or pass a symbol
    from a 'link' item to tj_get_prices. Top level: 28064 gold, 28066 coin, 28069 currency, 28426 crypto,
    28048 precious metals, 28049 oil and energy, 28042 commodities.
    """
    body = await fetch(f"{API}/v1/market/finder/list", {"id": parent_id} if parent_id else None)
    items = body["response"]["items"]
    return {
        "total": len(items),
        "items": [
            {"id": i.get("id"), "label": i.get("label"), "type": i.get("type"), "symbol": i.get("symbol")}
            for i in items[offset : offset + limit]
        ],
    }


@tool("Category price table")
async def tj_category_table(
    category: Annotated[
        str,
        Field(
            description="Preset (gold, coin, coin_retail, currency, currency_government, currency_sana, currency_nima, crypto) or a folder id from tj_list_categories, e.g. '28070'."
        ),
    ],
    limit: Annotated[int, Field(ge=1, le=50, description="Max rows (50 keeps the reply under 15 KB).")] = 25,
    offset: Annotated[int, Field(ge=0, description="Rows to skip.")] = 0,
) -> dict[str, Any]:
    """Live price table of one TGJU group: price, change, day high/low/open per symbol.

    Use for 'all gold prices', 'all coin prices', 'all currency rates'. Rial groups carry `price_toman`
    (Rial / 10); crypto is USD. A folder id gets the unit per row from the symbol-name rule (`unit: mixed`
    adds a `unit` to each row); unknown symbols, e.g. exchange-house quotes, stay `as_listed`. `stale` marks
    a quote older than 2 days. The crypto preset lists all
    ~27,000 coins in no useful order: use tj_get_prices for major coins and tj_search_symbols for the rest.
    """
    cid, default_unit = CATEGORIES.get(category, (category, None))
    if not cid.isdigit():
        raise ApiError(f"Unknown category '{category}'. Use a preset or a numeric folder id from tj_list_categories.")
    # The endpoint ignores `start` and pages with `page` (1-based, `length` rows each): fetch the pages covering the window.
    first, skip = divmod(offset, limit)
    data = []
    for page in (first + 1, first + 2)[: 2 if skip else 1]:
        body = await fetch(
            f"{API}/v1/market/list-data",
            {"category_ids": cid, "extra_data": 1, "lang": "fa", "page": page, "length": limit},
        )
        data += body["data"]
    rows, row_units = [], []
    for r in data[skip : skip + limit]:
        link = re.search(r'href="profile/([^"]+)">(.*?)</a>', r[0], re.S)
        d = _cells(r)
        t = re.sub(r"<[^>]+>", "", r[2])
        row = {
            "symbol": link and link.group(1),
            "title": link and re.sub(r"\s+", " ", link.group(2)).strip(),
            "price": d[1],
            "time": t,
            "stale": _stale(t) or None,
            "change": _signed(r[3], d[3]),
            "change_pct": _signed(r[4], d[4]),
            "high": d[5],
            "low": d[6],
            "open": d[7],
        }
        row_units.append(default_unit or _unit(row["symbol"] or ""))
        rows.append(_money(row, row_units[-1], "price", "change", "high", "low", "open"))
    kinds = set(row_units)
    unit = default_unit or (kinds.pop() if len(kinds) == 1 else "mixed" if kinds else "as_listed")
    if unit == "mixed":
        for row, u in zip(rows, row_units, strict=True):
            row["unit"] = u
    out = {"category": category, "unit": unit, "total": body["recordsTotal"], "offset": offset, "rows": rows}
    if not body["recordsTotal"]:
        out["note"] = (
            "No price rows in this folder (a parent folder or an unused market). Open it with tj_list_categories for sub-folders."
        )
    return out


async def _live() -> dict[str, dict[str, Any]]:
    return (await fetch(f"{CALL}/ajax.json"))["current"]


def _price(symbol: str, q: dict[str, Any]) -> dict[str, Any]:
    unit = _unit(symbol)
    p = {
        "symbol": symbol,
        "price": _num(q["p"]),
        "unit": unit,
        "change": _signed(f'class="{q.get("dt")}"', _num(q["d"])),
        "change_pct": _signed(f'class="{q.get("dt")}"', q.get("dp")),
        "high": _num(q["h"]),
        "low": _num(q["l"]),
        "time": q.get("ts"),
        "stale": _stale(q.get("ts")) or None,
    }
    return _money(p, unit, "price", "change", "high", "low")


@tool("Live prices")
async def tj_get_prices(
    symbols: Annotated[
        list[str],
        Field(
            min_length=1,
            max_length=30,
            description="Symbol slugs, e.g. ['price_dollar_rl', 'geram18', 'sekee', 'crypto-bitcoin'].",
        ),
    ],
) -> dict[str, Any]:
    """Live price, day change, high and low for one or more TGJU symbols.

    Use for current rates. Rial symbols also carry `*_toman`. `time` is the last update (Tehran time);
    old values mean the market is closed; `stale: true` marks a quote older than 2 days. Symbols missing
    from the live feed (slugs from tj_search_symbols) answer with their latest daily close (`source: history`,
    `time` = date). Unknown symbols are listed in `not_found`: find them with tj_search_symbols.
    """
    live = await _live()
    found, missing = [], []
    for s in symbols:
        key = s.strip()
        key = key if key in live else key.lower()
        if key in live:
            found.append(_price(key, live[key]))
        elif p := await _latest(key):
            found.append(p)
        else:
            missing.append(s)
    return {"prices": found, "not_found": missing}


@tool("Key rates summary")
async def tj_market_summary() -> dict[str, Any]:
    """Key Iranian market rates in one call: dollar, euro, dirham, pound, lira, gold gram and ounce, coins, silver, Brent, Bitcoin, Ethereum, Tether.

    Use first for 'what are today's rates'. Rial values carry `*_toman`; ounce, Brent, Bitcoin USD and
    Ethereum are USD. Drill into a group with tj_category_table.
    """
    live = await _live()
    return {
        "rates": [{"name": n, **_price(s, live[s])} for n, s in KEY_RATES if s in live],
    }


def _hist_row(r: list[str], unit: str) -> dict[str, Any]:
    d = _cells(r[:6])
    return _money(
        {
            "date": r[6],
            "jalali": r[7],
            "open": d[0],
            "low": d[1],
            "high": d[2],
            "close": d[3],
            # The site shows '-' for an unchanged close.
            "change": _signed(r[4], d[4]) or 0,
            "change_pct": _signed(r[5], d[5]) or 0,
        },
        unit,
        "open",
        "low",
        "high",
        "close",
        "change",
    )


async def _latest(symbol: str) -> dict[str, Any] | None:
    """Latest daily row of a symbol the live feed lacks, shaped like a live price; None if the site does not know it."""
    try:
        body = await fetch(
            f"{API}/v1/market/indicator/summary-table-data/{symbol}",
            {"lang": "fa", "start": 0, "length": 1, "order_col": "timestamp", "order_dir": "desc"},
        )
    except ApiError as e:
        if e.status != 500:
            raise
        return None
    if not body["data"]:
        return None
    unit = _unit(symbol)
    h = _hist_row(body["data"][0], unit)
    p = {
        "symbol": symbol,
        "price": h["close"],
        "unit": unit,
        **{k: h[k] for k in ("change", "change_pct", "high", "low")},
        "time": h["date"],
        "stale": _stale(h["date"]) or None,
        "source": "history",
    }
    return _money(p, unit, "price", "change", "high", "low")


@tool("Price history")
async def tj_price_history(
    symbol: Annotated[
        str,
        Field(
            min_length=1,
            description="Symbol slug, e.g. 'price_dollar_rl', 'geram18', 'sekee', 'ons', 'crypto-bitcoin'.",
        ),
    ],
    limit: Annotated[int, Field(ge=1, le=50, description="Max daily rows (50 keeps the reply under 15 KB).")] = 30,
    offset: Annotated[int, Field(ge=0, description="Rows to skip (for older pages).")] = 0,
    from_date: Annotated[
        str | None, Field(pattern=r"^\d{4}/\d{2}/\d{2}$", description="Jalali start date, e.g. '1405/07/01'.")
    ] = None,
    to_date: Annotated[
        str | None, Field(pattern=r"^\d{4}/\d{2}/\d{2}$", description="Jalali end date, e.g. '1405/07/10'.")
    ] = None,
    oldest_first: Annotated[bool, Field(description="Sort ascending by date (default newest first).")] = False,
) -> dict[str, Any]:
    """Daily history (open, low, high, close, change) of a TGJU symbol, for charts and trend questions.

    Use after tj_get_prices. Each row has Gregorian `date` and Jalali `jalali`; Rial symbols also carry
    `*_toman`. Days without a quote are missing. `total` is the number of rows in range: page with offset.
    """
    params: dict[str, Any] = {
        "lang": "fa",
        "start": offset,
        "length": limit,
        "order_col": "timestamp",
        "order_dir": "desc",
    }
    if from_date or to_date:
        params.update({"from": from_date or "1300/01/01", "to": to_date or "1500/01/01", "convert_to_ad": 1})
    url = f"{API}/v1/market/indicator/summary-table-data/{symbol.strip().lower()}"
    if oldest_first:
        # The site's own ascending order computes `change` against the NEXT day (wrong sign and size), so read
        # newest-first (change is vs the previous day) and reverse the window.
        total = (await fetch(url, {**params, "start": 0, "length": 1}))["recordsFiltered"]
        params.update({"start": max(total - offset - limit, 0), "length": max(min(limit, total - offset), 0)})
    body = await fetch(url, params) if params["length"] else {"data": [], "recordsFiltered": total}
    if oldest_first:
        body["data"] = body["data"][::-1]
    unit = _unit(symbol.strip().lower())
    rows = [_hist_row(r, unit) for r in body["data"]]
    return {"symbol": symbol, "unit": unit, "total": body["recordsFiltered"], "offset": offset, "rows": rows}
