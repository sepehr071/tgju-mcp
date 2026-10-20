import pytest

pytestmark = [pytest.mark.live, pytest.mark.anyio]


async def test_live_market_summary(client):
    result = await client.call_tool("tj_market_summary", {})
    rates = {r["name"]: r for r in result.structured_content["rates"]}
    assert rates["dollar"]["price_toman"] > 10_000
    assert rates["gold_ounce"]["price"] > 100


async def test_live_get_prices(client):
    result = await client.call_tool("tj_get_prices", {"symbols": ["geram18", "sekee"]})
    assert len(result.structured_content["prices"]) == 2


async def test_live_category_table(client):
    result = await client.call_tool("tj_category_table", {"category": "coin", "limit": 5})
    assert result.structured_content["rows"][0]["price_toman"] > 0


async def test_live_category_table_offset(client):
    first = await client.call_tool("tj_category_table", {"category": "currency", "limit": 5})
    later = await client.call_tool("tj_category_table", {"category": "currency", "limit": 5, "offset": 3})
    assert later.structured_content["rows"][0] == first.structured_content["rows"][3]


async def test_live_list_categories(client):
    result = await client.call_tool("tj_list_categories", {})
    assert result.structured_content["items"]


async def test_live_price_history(client):
    result = await client.call_tool("tj_price_history", {"symbol": "price_dollar_rl", "limit": 5})
    rows = result.structured_content["rows"]
    assert len(rows) == 5 and rows[0]["date"] > rows[1]["date"]


async def test_live_search(client):
    result = await client.call_tool("tj_search_symbols", {"query": "سکه امامی"})
    assert result.structured_content["matches"]


async def test_live_search_hits_work_in_prices(client):
    hits = await client.call_tool("tj_search_symbols", {"query": "irec"})
    symbols = [m["symbol"] for m in hits.structured_content["matches"][:3]]
    prices = await client.call_tool("tj_get_prices", {"symbols": symbols})
    assert not prices.structured_content["not_found"] and len(prices.structured_content["prices"]) == len(symbols)
