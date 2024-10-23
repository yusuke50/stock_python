from requests_html import HTML
import asyncio
from playwright.async_api import async_playwright


async def get_stock_info(stock_name):
    url = f"https://finance.yahoo.com/quote/{stock_name}/key-statistics"

    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge")
        page = await browser.new_page()
        try:
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            content = await page.content()
        finally:
            await browser.close()

    html = HTML(html=content)

    def extract_text(element):
        return element.text if element else None

    fifty_two_week_high = html.find(
        "article:nth-child(1) article > div.container > section:nth-child(2) > div.column section.card:nth-child(1) .table tr:nth-child(4) .value",
        first=True,
    )
    fifty_two_week_low = html.find(
        "article:nth-child(1) article > div.container > section:nth-child(2) > div.column section.card:nth-child(1) .table tr:nth-child(5) .value",
        first=True,
    )
    fifty_day_average = html.find(
        "article:nth-child(1) article > div.container > section:nth-child(2) > div.column section.card:nth-child(1) .table tr:nth-child(6) .value",
        first=True,
    )
    two_hundred_day_average = html.find(
        "article:nth-child(1) article > div.container > section:nth-child(2) > div.column section.card:nth-child(1) .table tr:nth-child(7) .value",
        first=True,
    )

    return {
        "fifty_two_week_high": extract_text(fifty_two_week_high),
        "fifty_two_week_low": extract_text(fifty_two_week_low),
        "fifty_day_average": extract_text(fifty_day_average),
        "two_hundred_day_average": extract_text(two_hundred_day_average),
    }
