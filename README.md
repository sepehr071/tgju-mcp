<!-- mcp-name: io.github.sepehr071/tgju-mcp -->

# tgju-mcp: TGJU MCP server for AI agents (dollar, gold, coin and crypto prices in Iran)

**Let your AI agent read live Iranian market prices from TGJU (tgju.org).**<br>
An unofficial, read-only MCP server for [TGJU](https://www.tgju.org) (شبکه اطلاع&zwnj;رسانی طلا، سکه و ارز), Iran's market-price portal:<br>
dollar, euro, gold, coin, crypto and commodity prices, category tables and daily history, from Claude, Cursor or Copilot.

[![PyPI](https://img.shields.io/pypi/v/tgju-mcp?color=2563eb)](https://pypi.org/project/tgju-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/tgju-mcp)](https://pypi.org/project/tgju-mcp/)
[![CI](https://github.com/sepehr071/tgju-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/sepehr071/tgju-mcp/actions/workflows/ci.yml)
[![MCP Registry](https://img.shields.io/badge/MCP_Registry-io.github.sepehr071%2Ftgju--mcp-7c3aed)](https://registry.modelcontextprotocol.io/?q=tgju-mcp)
[![License: MIT](https://img.shields.io/badge/license-MIT-16a34a)](https://github.com/sepehr071/tgju-mcp/blob/main/LICENSE)

[![Install in VS Code](https://img.shields.io/badge/VS_Code-Install_tgju--mcp-0098FF?style=flat-square&logo=visualstudiocode&logoColor=white)](https://vscode.dev/redirect/mcp/install?name=tgju&config=%7B%22command%22%3A%22uvx%22%2C%22args%22%3A%5B%22tgju-mcp%22%5D%7D)

[For AI agents](#for-ai-agents) · [Why](#why) · [What it can do](#what-it-can-do) · [Quick start](#quick-start) · [Tools](#tools) · [How it works](#how-it-works) · [Good to know](#good-to-know) · [FAQ](#faq) · [Configuration](#configuration) · [فارسی](#فارسی) · [Development](#development)

---

## For AI agents

- **What:** unofficial MCP server (model context protocol) for tgju.org, the Iranian portal for dollar, gold, coin, crypto and commodity prices. Symbol search takes Persian and English names.
- **Install:** `uvx tgju-mcp` or `claude mcp add tgju -- uvx tgju-mcp`. Transport: stdio. Needs [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python 3.10+).
- **Auth:** none, no API key or account. Optional `TGJU_MCP_PROXY` (HTTP proxy URL, or a comma-separated list); system proxy settings are ignored.
- **Access:** read-only. It cannot log in or trade, so no confirmation is needed before calling any tool.
- **Tools:** 6, all prefixed `tj_`. Typical sequence: `tj_market_summary` -> `tj_category_table` -> `tj_price_history`.
  If you only have a name, call `tj_search_symbols` first and pass its `symbol` to the other tools.
- **Use when:** the user asks for the dollar, euro, gold, coin, Bitcoin or Brent price in Iran, a price table of a group, or a symbol's daily history.
- **Do not use when:** the user wants to trade or buy anything, needs stock-exchange (TSETMC) data, or asks about markets outside the TGJU feed.
- **Output:** compact JSON. Iranian prices are quoted by the site in **Rial**; those symbols also carry `*_toman` (Rial / 10). Global symbols (ounce, Brent, crypto in USD, currency pairs) keep their listed unit (`unit: as_listed`).
- **Machine-readable:** [`server.json`](https://github.com/sepehr071/tgju-mcp/blob/main/server.json) and the
  [awesome-iran-mcp catalog](https://github.com/sepehr071/awesome-iran-mcp).

## Why

TGJU is where Iranians check the dollar, gold and coin price, but it is a busy web page with hundreds of symbols.
Asking "what is the dollar, the 18k gold gram and the Emami coin right now, and how did the dollar move over the last
month?" means several screens. With `tgju-mcp` an agent answers it in a few calls and returns a short summary
instead of raw tables.

> **You:** What are the main rates today, and how has the dollar moved recently?
>
> **Agent:** *calls* `tj_market_summary` -> `tj_search_symbols` -> `tj_price_history`
>
> It reads the key rates in one call, finds the dollar symbol, and summarises its recent daily closes.

Every reply is trimmed to stay under about 15 KB, so it does not flood the agent's context.

## What it can do

- **Summarise the market** in one call: dollar, euro, dirham, pound, lira, gold gram and ounce, coins, silver, Brent, Bitcoin, Ethereum, Tether
- **Quote symbols**: live price, change, high and low for one or more symbols
- **List price tables** of a group: gold, coin, retail coin, currency, government currency, Sana, Nima, crypto, or any folder id
- **Browse the market tree** to find folders and symbols
- **Search symbols** by name across internal, global and crypto markets
- **Pull daily history**: open, low, high, close and change, with Jalali date filters
- **Read-only by design**: no login, no trading

Example prompts:

- "What is the dollar, euro and 18k gold gram price right now?"
- "Show the coin price table."
- "How has the free-market dollar moved over the last 30 days?"
- "Price of Bitcoin and Tether in Toman."
- "Find the symbol for Brent oil and show its latest price."
- <span dir="rtl">قیمت دلار، یورو و طلای ۱۸ عیار الان چند است؟</span>
- <span dir="rtl">جدول قیمت سکه امروز را نشان بده.</span>
- <span dir="rtl">روند قیمت دلار در یک ماه گذشته چطور بوده؟</span>

## Quick start

You need [uv](https://docs.astral.sh/uv/getting-started/installation/). No API key or account.

<details open>
<summary><b>Claude Code</b></summary>

```bash
claude mcp add tgju -- uvx tgju-mcp
```
</details>

<details>
<summary><b>Claude Desktop</b></summary>

Settings → Developer → Edit Config, then add:

```json
{
  "mcpServers": {
    "tgju": { "command": "uvx", "args": ["tgju-mcp"] }
  }
}
```
</details>

<details>
<summary><b>Cursor</b></summary>

Add the Claude Desktop block above to `~/.cursor/mcp.json` (or `.cursor/mcp.json` in a project).
</details>

<details>
<summary><b>VS Code (Copilot agent mode)</b></summary>

Click **Install in VS Code** above, or add to `.vscode/mcp.json`:

```json
{
  "servers": {
    "tgju": { "type": "stdio", "command": "uvx", "args": ["tgju-mcp"] }
  }
}
```
</details>

<details>
<summary><b>Codex CLI</b></summary>

```bash
codex mcp add tgju -- uvx tgju-mcp
```

Or in `~/.codex/config.toml`:

```toml
[mcp_servers.tgju]
command = "uvx"
args = ["tgju-mcp"]
```
</details>

<details>
<summary><b>Gemini CLI</b></summary>

Add to `~/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "tgju": { "command": "uvx", "args": ["tgju-mcp"] }
  }
}
```
</details>

<details>
<summary><b>Windsurf</b></summary>

Add the Claude Desktop block to `~/.codeium/windsurf/mcp_config.json`.
</details>

<details>
<summary><b>Anything else</b></summary>

It is a standard stdio MCP server: run `uvx tgju-mcp`, or `pip install tgju-mcp` and run `tgju-mcp`.
</details>

## Tools

Symbols are lower-case slugs such as `price_dollar_rl`, `geram18` or `sekee`. If you do not know one, call `tj_search_symbols` first.

| Tool | What it does |
|---|---|
| `tj_market_summary` | Key Iranian market rates in one call: dollar, euro, dirham, pound, lira, gold gram and ounce, coins, silver, Brent, Bitcoin, Ethereum, Tether |
| `tj_get_prices` | Live price, day change, high and low for one or more TGJU symbols |
| `tj_category_table` | Live price table of one TGJU group: price, change, day high/low/open per symbol |
| `tj_list_categories` | Browse TGJU's market tree: folders (with ids) and symbols |
| `tj_search_symbols` | Find TGJU symbols by name |
| `tj_price_history` | Daily history (open, low, high, close, change) of a TGJU symbol, for charts and trend questions |

All 6 tools are annotated `readOnlyHint: true`.

## How it works

```text
  AI agent  (Claude, Cursor, Copilot, ...)
      │
      │  MCP over stdio
      ▼
  tgju-mcp  (runs on your machine)
      │
      │  HTTPS
      └──────▶  api.tgju.org, call4.tgju.org   live feed, tables, history, search
```

`tgju-mcp` runs locally and calls the same endpoints the tgju.org site uses. It has no hosted server in between and
no API key. Requests go out through a Chrome-impersonating client, at most 2 at a time with a little jitter. Answers
are kept for 15 seconds, a failed GET is retried, and it only talks to `api.tgju.org` and `call4.tgju.org`. It only reads.

## Good to know

- **Units:** the feed has no unit field. Gold grams, coins, free-market and other `price_*` currencies and `crypto-*-irr` are in Rial (`*_toman` = Rial / 10). `ons`, `silver`, `oil_*`, `crypto-*` (USD) and pairs like `usd-try-ask` keep their listed unit (`as_listed`).
- **Unit rule is a heuristic** on the symbol name, so check unusual symbols against tgju.org. Folder-id tables apply it per row (`unit: mixed`); symbols outside it, such as exchange-house quotes with slug names, stay `as_listed`.
- **Reply caps:** `tj_category_table` and `tj_price_history` return at most 50 rows, so replies stay under about 14 KB.
- **Stale quotes:** a quote older than 2 days carries `stale: true`. Illiquid symbols can be delayed, so check `time`.
- **Symbols missing from the live feed** (slugs from `tj_search_symbols`) are answered by `tj_get_prices` with the latest daily close (`source: history`, `time` = date).
- **Dates:** history returns Gregorian and Jalali dates; `from_date` and `to_date` filters are Jalali `YYYY/MM/DD`.
- **Search** returns at most 10 hits.
- **What it does not do:** no trading or orders, no account features, no prices outside the TGJU feed.
- **Network:** tgju.org answered plain requests from both a proxy and a direct connection when tested. If your network blocks it, set `TGJU_MCP_PROXY`. System proxy variables are ignored on purpose.

## FAQ

<details>
<summary><b>Is there a TGJU API or MCP server?</b></summary>

TGJU has no documented public API. `tgju-mcp` is an unofficial MCP server with 6 read-only tools that calls the same
endpoints the tgju.org web app uses and returns compact JSON for AI agents.
</details>

<details>
<summary><b>How do I get the dollar or gold price in Claude, Cursor or Copilot?</b></summary>

Add the server with `claude mcp add tgju -- uvx tgju-mcp`, or use the matching config in
[Quick start](#quick-start), then ask in plain language, in Persian or English.
</details>

<details>
<summary><b>Are prices in Rial or Toman?</b></summary>

TGJU quotes Iranian prices in Rial. Those symbols also come back as `*_toman` (Rial / 10). Global symbols such as the
gold ounce, Brent and crypto in USD keep their listed unit.
</details>

<details>
<summary><b>Which symbol do I use for the dollar?</b></summary>

Call `tj_market_summary` for the main rates, or `tj_search_symbols` with a name (Persian or English) and pass the
returned `symbol` to `tj_get_prices` or `tj_price_history`.
</details>

<details>
<summary><b>Why does a price look old?</b></summary>

Some symbols are illiquid or no longer updated. A quote older than 2 days is marked `stale: true`; check the `time` field.
</details>

<details>
<summary><b>Can it buy gold or give investment advice?</b></summary>

No. It has no login and no trading calls, it only reads public prices. Nothing it returns is financial advice.
</details>

<details>
<summary><b>Is the data real time?</b></summary>

It is what TGJU serves, kept for up to 15 seconds in a local cache, and it may be delayed.
</details>

<details>
<summary><b>How do I debug what the agent sees?</b></summary>

```bash
npx @modelcontextprotocol/inspector uvx tgju-mcp
```
</details>

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `TGJU_MCP_PROXY` | unset | Optional HTTP proxy URL for tgju.org requests; system proxy settings are ignored. Also accepts a comma-separated list: one is used until it gets blocked or fails to connect, then the next |

<a id="فارسی"></a>

## فارسی: سرور MCP قیمت دلار، طلا و سکه (TGJU)

<div dir="rtl">

**tgju-mcp** یک سرور MCP غیررسمی و فقط&zwnj;خواندنی برای سایت TGJU (شبکه اطلاع&zwnj;رسانی طلا، سکه و ارز) است. این سرور به دستیار هوش مصنوعی شما (Claude، Cursor، Copilot و ...) اجازه می&zwnj;دهد
قیمت دلار، یورو، طلا، سکه، ارز دیجیتال و کالاها را از tgju.org بخواند.

**چه کارهایی می&zwnj;کند**

- **خلاصه بازار** در یک فراخوانی: دلار، یورو، درهم، پوند، لیر، گرم و اونس طلا، سکه&zwnj;ها، نقره، برنت، بیت&zwnj;کوین، اتریوم و تتر.
- **قیمت لحظه&zwnj;ای نماد** با تغییر روز، بیشترین و کمترین قیمت.
- **جدول قیمت گروه&zwnj;ها**: طلا، سکه، ارز، ارز دولتی، ارز نیما، ارز سنا، ارز دیجیتال.
- **جستجوی نماد** و گشت&zwnj;وگذار در درخت بازار.
- **تاریخچه روزانه** قیمت (باز، کم، زیاد، پایانی و تغییر) با فیلتر تاریخ شمسی، تا ۵۰ ردیف.

**نکته&zwnj;ها**

- فقط خواندنی است: وارد حساب نمی&zwnj;شود و خرید و فروش انجام نمی&zwnj;دهد. توصیه مالی نیست.
- قیمت&zwnj;های ایرانی در سایت به ریال است و برای آن&zwnj;ها فیلد تومان (ریال تقسیم بر ۱۰) هم برمی&zwnj;گردد. نمادهای جهانی (اونس، برنت، ارز دیجیتال به دلار) واحد خودشان را دارند.
- قیمت نمادهای کم&zwnj;معامله ممکن است قدیمی باشد؛ فیلد `time` را ببینید.
- کلید API لازم نیست و روی سیستم خود شما اجرا می&zwnj;شود. در صورت نیاز به پراکسی، متغیر `TGJU_MCP_PROXY` را بگذارید.

**نصب** (اول [uv](https://docs.astral.sh/uv/getting-started/installation/) را نصب کنید). در Claude Code:

</div>

```bash
claude mcp add tgju -- uvx tgju-mcp
```

<div dir="rtl">

در Claude Desktop، Cursor و بقیه برنامه&zwnj;ها همان تنظیم بخش [Quick start](#quick-start) را بگذارید.

**نمونه پرسش&zwnj;ها**

- «قیمت دلار و طلای ۱۸ عیار الان چند است؟»
- «جدول قیمت سکه را نشان بده.»
- «روند دلار آزاد در ۳۰ روز گذشته چطور بوده؟»
- «قیمت بیت&zwnj;کوین و تتر به تومان چقدر است؟»

</div>

## Development

```bash
git clone https://github.com/sepehr071/tgju-mcp && cd tgju-mcp
uv sync
uv run ruff check . && uv run ruff format --check .
uv run python -m pytest -q          # offline unit tests
uv run python -m pytest -m live -q  # calls tgju.org
uv build
```

All tools live in `src/tgju_mcp/markets.py`; each is a typed async function with a docstring that tells the agent
when to use it. Issues and PRs are welcome.

Releases: bump the version in `pyproject.toml` and `server.json`, then push a `v*` tag. GitHub Actions publishes to PyPI.

## Related servers

- [awesome-iran-mcp](https://github.com/sepehr071/awesome-iran-mcp): catalog of all Iranian-service MCP servers
- [tsetmc-mcp](https://github.com/sepehr071/tsetmc-mcp) for Tehran Stock Exchange quotes and indices
- [iran-crypto-mcp](https://github.com/sepehr071/iran-crypto-mcp) for crypto prices on Iranian exchanges
- [milligold-mcp](https://github.com/sepehr071/milligold-mcp) for gold prices on Milli
- [iran-news-mcp](https://github.com/sepehr071/iran-news-mcp) for Iranian news

## Disclaimer

Unofficial and not affiliated with or endorsed by TGJU. It is read-only and uses the endpoints of the tgju.org web
app, which can change without notice. Prices are informational, may be delayed, and are not financial advice.

## Author

<a href="https://www.linkedin.com/in/sepehr-radmard"><img src="https://raw.githubusercontent.com/sepehr071/awesome-iran-mcp/main/assets/author-banner.png" alt="Sepehr Radmard: open-source MCP servers for the Iranian web. LinkedIn: linkedin.com/in/sepehr-radmard" width="100%"></a>

Built and maintained by **Sepehr Radmard** (سپهر رادمرد). Connect on [LinkedIn](https://www.linkedin.com/in/sepehr-radmard) or follow [@sepehr071 on GitHub](https://github.com/sepehr071) for more MCP servers for Iranian websites, all listed in [awesome-iran-mcp](https://github.com/sepehr071/awesome-iran-mcp). If this saves you time, a star on the repo helps other people find it.

## License

[MIT](https://github.com/sepehr071/tgju-mcp/blob/main/LICENSE)
