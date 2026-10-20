# tgju-mcp

Unofficial, read-only MCP server for TGJU (tgju.org), Iranian market prices. Copies the layout and idioms of
`../snapp-mcp`. On GitHub (`sepehr071/tgju-mcp`, public), not yet tagged or released (PyPI `tgju-mcp` planned).
API map: `../tgju/README.md`.

## Layout

- `src/tgju_mcp/http.py`: the only HTTP code. One shared `httpx.AsyncClient` (`trust_env=False`) on a Chrome-impersonating
  curl_cffi transport, proxy only from `TGJU_MCP_PROXY` (comma list, sticky), concurrency 2, jitter, 15 s GET cache,
  GET retries, host allowlist (`api.tgju.org`, `call4.tgju.org`), 5 MB body cap, `fetch(url, params)`, `ApiError`, `set_transport()` for tests.
  No bot-check/browser fallback (tgju.org served plain requests from both the proxy and a direct connection).
- `registry.py`: `@tool("Title")`. `server.py`: registration, read-only annotations, `INSTRUCTIONS`.
- `markets.py`: all 6 tools (`tj_market_summary`, `tj_get_prices`, `tj_category_table`, `tj_list_categories`, `tj_search_symbols`, `tj_price_history`).
- `tests/`: `test_markets.py` (MockTransport + trimmed real fixtures), `test_live_markets.py` (`@pytest.mark.live`).

## Commands

```bash
uv sync
uv run ruff check . && uv run ruff format --check .
uv run python -m pytest -q
uv run python -m pytest -m live -q
uv build
```

uv downloads may need the local proxy (`HTTPS_PROXY=http://127.0.0.1:10898`) when it is on; the server and tests never use env proxies.

## Rules for changes

- Read-only only. New tool: `@tool("Title")`, `Annotated[..., Field(...)]` params with examples, one-sentence first docstring line, unit test with fixture, live test, README row, `INSTRUCTIONS` mention.
- Keep README tool table equal to `list_tools()`. Deps stay `mcp`, `httpx`, `httpx-curl-cffi`, `curl-cffi`.

## TGJU quirks

- Live feed: `GET call4.tgju.org/ajax.json` (call..call5 identical), `current` = ~1050 symbols `{p,h,l,d,dp,dt,ts}`, numbers as strings with commas; `dt` high/low is the direction of `d`/`dp`.
- Units are not in the feed. Rial: gold grams, coins, `price_*` currencies, `crypto-*-irr`; `usdt-irr` is stale since 2020 (use `crypto-tether-irr`, Rial). `_RIAL` in `markets.py` is a name heuristic; `*_toman` fields only exist for matches.
- Tables (`list-data`, `summary-table-data`) are DataTables JSON: HTML cells; a change cell with `class="low"` is a fall. `start`/`length` page them. History filters `from`/`to` take Jalali dates and need `convert_to_ad=1`; Gregorian dates give HTTP 500. Unknown symbol = HTTP 500.
- Replies must stay under ~15 KB: `tj_category_table` and `tj_price_history` cap `limit` at 50 (about 13 KB for `sekee` history, `currency_government`). `stale` = quote older than 2 days (`_stale` in `markets.py`; table times are `HH:MM:SS` or a yearless Jalali date).
- Search (`/v1/search?q=`, not `keyword=`) returns Elasticsearch JSON as strings per module, max 10 hits. `grade` is a live-feed key only for main symbols; otherwise the search returns the slug, and `tj_get_prices` falls back to the latest history row.

## Release

Bump `version` in `pyproject.toml` and both versions in `server.json`, update `uv.lock`, commit, `git tag vX.Y.Z && git push --tags`; `.github/workflows/publish.yml` does the rest.
