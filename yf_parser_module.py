from requests_html import HTML
import asyncio
from playwright.async_api import async_playwright


_playwright = None
_browser = None
_browser_lock = asyncio.Lock()


async def _get_browser():
    global _playwright, _browser
    async with _browser_lock:
        if _browser is None or not _browser.is_connected():
            if _playwright is None:
                _playwright = await async_playwright().start()
            _browser = await _playwright.chromium.launch(channel="msedge", headless=True)
    return _browser


async def close_browser():
    global _playwright, _browser
    if _browser is not None:
        await _browser.close()
        _browser = None
    if _playwright is not None:
        await _playwright.stop()
        _playwright = None


async def get_stock_info(stock_name):
    url = f"https://finance.yahoo.com/quote/{stock_name}/key-statistics"

    browser = await _get_browser()
    page = await browser.new_page()
    try:
        await page.goto(url, timeout=60000, wait_until="domcontentloaded")
        content = await page.content()
    finally:
        await page.close()

    html = HTML(html=content)

    def extract_text(element):
        return element.text if element else None

    fifty_two_week_high = html.find(
        "section:nth-child(1) article > div.container > section:nth-child(2) > div.column section.card:nth-child(1) .table tr:nth-child(4) .value",
        first=True,
    )
    fifty_two_week_low = html.find(
        "section:nth-child(1) article > div.container > section:nth-child(2) > div.column section.card:nth-child(1) .table tr:nth-child(5) .value",
        first=True,
    )
    fifty_day_average = html.find(
        "section:nth-child(1) article > div.container > section:nth-child(2) > div.column section.card:nth-child(1) .table tr:nth-child(6) .value",
        first=True,
    )
    two_hundred_day_average = html.find(
        "section:nth-child(1) article > div.container > section:nth-child(2) > div.column section.card:nth-child(1) .table tr:nth-child(7) .value",
        first=True,
    )

    return {
        "fifty_two_week_high": extract_text(fifty_two_week_high),
        "fifty_two_week_low": extract_text(fifty_two_week_low),
        "fifty_day_average": extract_text(fifty_day_average),
        "two_hundred_day_average": extract_text(two_hundred_day_average),
    }
