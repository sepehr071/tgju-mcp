import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from conftest import fixture

from tgju_mcp import markets

pytestmark = pytest.mark.anyio


async def test_all_tools_are_read_only(client):
    tools = (await client.list_tools()).tools
    assert {t.name for t in tools} == {
        "tj_search_symbols",
        "tj_list_categories",
        "tj_category_table",
        "tj_get_prices",
        "tj_market_summary",
        "tj_price_history",
    }
    for t in tools:
        assert t.annotations.read_only_hint is True, t.name
        assert t.description and t.title, t.name


async def test_get_prices_rial_and_usd(client, api):
    api["/ajax.json"] = fixture("ajax.json")
    api["/v1/market/indicator/summary-table-data/nope"] = lambda r: httpx.Response(500, text="")
    result = await client.call_tool("tj_get_prices", {"symbols": ["price_dollar_rl", "crypto-bitcoin", "nope"]})
    dollar, btc = result.structured_content["prices"]
    assert dollar["unit"] == "rial" and dollar["price_toman"] == dollar["price"] / 10
    assert btc["unit"] == "as_listed" and "price_toman" not in btc
    assert result.structured_content["not_found"] == ["nope"]


async def test_fall_has_negative_change(client, api):
    api["/ajax.json"] = fixture("ajax.json")
    ons = fixture("ajax.json")["current"]["ons"]
    assert ons["dt"] == "low"
    result = await client.call_tool("tj_get_prices", {"symbols": ["ons"]})
    assert result.structured_content["prices"][0]["change"] < 0


async def test_market_summary(client, api):
    api["/ajax.json"] = fixture("ajax.json")
    rates = {r["name"]: r for r in (await client.call_tool("tj_market_summary", {})).structured_content["rates"]}
    assert rates["gold_18k_gram"]["price_toman"] > 1_000_000
    assert rates["tether"]["unit"] == "rial" and rates["tether"]["price_toman"] > 100_000
    assert rates["bitcoin_irr"]["unit"] == "rial"


async def test_category_table(client, api):
    api["/v1/market/list-data"] = fixture("list_data_gold.json")
    result = await client.call_tool("tj_category_table", {"category": "gold", "limit": 3})
    rows = result.structured_content["rows"]
    assert rows[0]["symbol"] == "geram18" and rows[0]["price_toman"] == rows[0]["price"] / 10
    sent = api.calls[0].url.params
    assert sent["category_ids"] == "91818" and sent["length"] == "3"


async def test_category_table_offset_uses_pages(client, api):
    api["/v1/market/list-data"] = fixture("list_data_gold.json")
    result = await client.call_tool("tj_category_table", {"category": "gold", "limit": 2, "offset": 3})
    sent = [c.url.params for c in api.calls]
    assert [p["page"] for p in sent] == ["2", "3"] and all(p["length"] == "2" for p in sent)
    assert "start" not in sent[0]
    assert result.structured_content["offset"] == 3


async def test_category_table_empty_folder_has_note(client, api):
    api["/v1/market/list-data"] = {"draw": 1, "recordsTotal": 0, "recordsFiltered": 0, "data": []}
    result = await client.call_tool("tj_category_table", {"category": "28048"})
    assert result.structured_content["rows"] == [] and "tj_list_categories" in result.structured_content["note"]


async def test_category_unknown(client, api):
    result = await client.call_tool("tj_category_table", {"category": "banana"})
    assert result.is_error


async def test_list_categories(client, api):
    api["/v1/market/finder/list"] = fixture("finder_coin.json")
    result = await client.call_tool("tj_list_categories", {"parent_id": "28066", "limit": 2})
    assert len(result.structured_content["items"]) == 2
    assert api.calls[0].url.params["id"] == "28066"


async def test_price_history(client, api):
    api["/v1/market/indicator/summary-table-data/price_dollar_rl"] = fixture("history_dollar.json")
    result = await client.call_tool(
        "tj_price_history",
        {"symbol": "price_dollar_rl", "limit": 3, "from_date": "1405/07/01", "to_date": "1405/07/10"},
    )
    first = result.structured_content["rows"][0]
    assert first["open"] <= first["high"] and first["low"] <= first["close"] <= first["high"]
    assert first["change"] < 0  # the site marks the day as a fall
    assert first["close_toman"] == first["close"] / 10
    sent = api.calls[0].url.params
    assert sent["from"] == "1405/07/01" and sent["convert_to_ad"] == "1"


async def test_price_history_dash_change_is_zero(client, api):
    body = fixture("history_dollar.json")
    body["data"][0][4], body["data"][0][5] = '<span class="" dir="ltr">-</span>', "-"
    api["/v1/market/indicator/summary-table-data/price_dollar_rl"] = body
    row = (await client.call_tool("tj_price_history", {"symbol": "price_dollar_rl", "limit": 1})).structured_content[
        "rows"
    ][0]
    assert row["change"] == 0 and row["change_pct"] == 0


async def test_price_history_oldest_first_reads_newest_first(client, api):
    api["/v1/market/indicator/summary-table-data/price_dollar_rl"] = fixture("history_dollar.json")
    result = await client.call_tool("tj_price_history", {"symbol": "price_dollar_rl", "limit": 2, "oldest_first": True})
    sent = [c.url.params for c in api.calls]
    assert all(p["order_dir"] == "desc" for p in sent)
    assert (sent[1]["start"], sent[1]["length"]) == ("3978", "2")  # total 3980: the 2 oldest rows
    dates = [r["date"] for r in result.structured_content["rows"]]
    assert dates == sorted(dates)


async def test_search_symbols(client, api):
    api["/v1/search"] = fixture("search_coin.json")
    api["/ajax.json"] = fixture("ajax.json")
    result = await client.call_tool("tj_search_symbols", {"query": "سکه امامی"})
    assert result.structured_content["matches"][0]["symbol"] == "sekee"


async def test_search_symbol_not_in_live_feed_is_the_slug(client, api):
    body = fixture("search_coin.json")
    raw = json.loads(body["response"]["result"]["markets.internal"])
    raw["hits"]["hits"][0]["_source"]["grade"] = "irec-sell"  # shared by every exchange house
    body["response"]["result"]["markets.internal"] = json.dumps(raw)
    api["/v1/search"] = body
    api["/ajax.json"] = fixture("ajax.json")
    match = (await client.call_tool("tj_search_symbols", {"query": "سکه امامی"})).structured_content["matches"][0]
    assert match["symbol"] == match["slug"] == "سکه-امامی-2"


async def test_get_prices_falls_back_to_latest_history_row(client, api):
    api["/ajax.json"] = fixture("ajax.json")
    slug = "سکه-امامی-فروش-221"
    api[f"/v1/market/indicator/summary-table-data/{slug}"] = fixture("history_dollar.json")
    api["/v1/market/indicator/summary-table-data/zzz"] = lambda r: httpx.Response(500, text="")
    result = await client.call_tool("tj_get_prices", {"symbols": ["sekee", slug, "zzz"]})
    live, hist = result.structured_content["prices"]
    assert "source" not in live and hist["source"] == "history" and hist["symbol"] == slug
    assert hist["price"] == 2628000 and hist["time"]
    assert api.calls[-2].url.params["length"] == "1"
    assert result.structured_content["not_found"] == ["zzz"]


async def test_get_prices_flags_stale_quote(client, api, monkeypatch):
    body = fixture("ajax.json")
    body["current"]["gerami"]["ts"] = "2026-10-16 11:00:34"
    api["/ajax.json"] = body
    monkeypatch.setattr(markets, "_now", lambda: datetime(2026, 10, 19, 23, 57, tzinfo=timezone(timedelta(hours=3.5))))
    prices = (await client.call_tool("tj_get_prices", {"symbols": ["gerami", "sekee"]})).structured_content["prices"]
    assert prices[0]["stale"] is True and "stale" not in prices[1]


def test_stale_cells(monkeypatch):
    monkeypatch.setattr(markets, "_now", lambda: datetime(2026, 10, 19, 23, 57, tzinfo=timezone(timedelta(hours=3.5))))
    assert not markets._stale("۱۹:۵۹:۵۵") and not markets._stale("2026-10-17 00:00:00")
    assert markets._stale("2026-10-16 23:00:00") and markets._stale("2026/10/10")
    assert not markets._stale("۲۷ مهر") and not markets._stale("۲۵ مهر") and markets._stale("۲۴ مهر")
    assert markets._stale("۱۷ خرداد") and not markets._stale(None) and not markets._stale("-")


async def test_category_table_flags_stale_rows(client, api, monkeypatch):
    monkeypatch.setattr(markets, "_now", lambda: datetime(2026, 10, 19, 23, 57, tzinfo=timezone(timedelta(hours=3.5))))
    body = fixture("list_data_gold.json")
    body["data"][1][2] = "۱۷ خرداد"
    api["/v1/market/list-data"] = body
    rows = (await client.call_tool("tj_category_table", {"category": "gold", "limit": 3})).structured_content["rows"]
    assert [r.get("stale") for r in rows] == [None, True, None]


async def test_category_table_folder_id_gets_unit_per_row(client, api):
    api["/v1/market/list-data"] = fixture("list_data_gold.json")
    out = (await client.call_tool("tj_category_table", {"category": "91820", "limit": 3})).structured_content
    assert out["unit"] == "rial" and out["rows"][0]["price_toman"] == out["rows"][0]["price"] / 10
    body = fixture("list_data_gold.json")
    body["data"][1][0] = '<a href="profile/kajex_gbp_sell">پوند / فروش</a>'
    api["/v1/market/list-data"] = body
    out = (await client.call_tool("tj_category_table", {"category": "28249", "limit": 3})).structured_content
    assert out["unit"] == "mixed" and [r["unit"] for r in out["rows"]][:2] == ["rial", "as_listed"]
    assert "price_toman" not in out["rows"][1]


async def test_reply_size_limits(client, api):
    assert (await client.call_tool("tj_category_table", {"category": "gold", "limit": 51})).is_error
    assert (await client.call_tool("tj_price_history", {"symbol": "geram18", "limit": 51})).is_error


async def test_unknown_symbol_is_actionable(client, api):
    api["/v1/market/indicator/summary-table-data/zzz"] = lambda r: httpx.Response(500, text="")
    result = await client.call_tool("tj_price_history", {"symbol": "zzz"})
    assert result.is_error
    assert "tj_search_symbols" in result.content[0].text
