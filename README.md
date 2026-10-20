<!-- mcp-name: io.github.sepehr071/tgju-mcp -->

# tgju-mcp: TGJU prices MCP server for AI agents

An unofficial, read-only MCP server for [TGJU](https://www.tgju.org) (شبکه اطلاع‌رسانی طلا، سکه و ارز), Iran's market-price portal:
live dollar, euro, gold, coin, crypto and commodity prices, category tables, and daily history.

## For AI agents

- **What:** unofficial MCP server for tgju.org prices. Persian and English queries work for symbol search.
- **Install:** `uvx tgju-mcp` or `claude mcp add tgju -- uvx tgju-mcp`. Transport: stdio. Needs [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python 3.10+).
- **Auth:** none. Optional `TGJU_MCP_PROXY` (HTTP proxy URL, or a comma-separated list); system proxy settings are ignored.
- **Access:** read-only, so no confirmation is needed before calling any tool.
- **Tools:** 6, all prefixed `tj_`. Typical sequence: `tj_market_summary` -> `tj_category_table` -> `tj_price_history`.
- **Output:** compact JSON. Iranian prices are quoted by the site in **Rial**; rial symbols also carry `*_toman` (Rial / 10). Global symbols (ounce, Brent, crypto in USD, currency pairs) keep their listed unit (`unit: as_listed`).
- **Machine-readable:** [`server.json`](server.json).

## Tools

| Tool | Purpose |
|---|---|
| `tj_market_summary` | Key rates in one call: dollar, euro, dirham, pound, lira, gold gram/ounce, coins, silver, Brent, Bitcoin, Ethereum, Tether |
| `tj_get_prices` | Live price, change, high and low for one or more symbols |
| `tj_category_table` | Live price table of a group (gold, coin, coin_retail, currency, currency_government, currency_sana, currency_nima, crypto, or a folder id) |
| `tj_list_categories` | Browse the market tree (folders and symbols) |
| `tj_search_symbols` | Find symbols by name (internal, global or crypto markets) |
| `tj_price_history` | Daily open, low, high, close and change of a symbol, with Jalali date filters |

## Units

| Symbols | Unit |
|---|---|
| Gold grams, coins, free-market and other `price_*` currencies, `crypto-*-irr` | Rial (`*_toman` = Rial / 10) |
| `ons`, `silver`, `oil_*`, `crypto-*` (USD), currency pairs like `usd-try-ask` | as listed (USD or a ratio) |

The feed carries no unit field: the Rial/Toman split is a rule on the symbol name, so check unusual symbols against tgju.org.
Folder-id tables apply the rule per row (`unit: mixed` adds a `unit` to each row); symbols outside it, such as exchange-house quotes with slug names, stay `as_listed`.

## Reply size and staleness

`tj_category_table` and `tj_price_history` accept at most 50 rows (replies stay under about 14 KB). A quote older than 2 days carries `stale: true`. `tj_get_prices` answers symbols missing from the live feed (slugs from `tj_search_symbols`) with the latest daily close (`source: history`, `time` = date).

## Development

```bash
uv sync
uv run ruff check . && uv run ruff format --check .
uv run python -m pytest -q          # offline unit tests
uv run python -m pytest -m live -q  # calls tgju.org
uv build
```

Not affiliated with TGJU. Prices are informational, not financial advice. MIT license.
