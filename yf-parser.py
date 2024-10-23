from requests_html import HTML
import asyncio
from playwright.async_api import async_playwright


async def get_stock_info(stock_name):
    url = f"https://finance.yahoo.com/quote/{stock_name}/key-statistics"

    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
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

    if fifty_two_week_high:
        print(f"52 week high: {extract_text(fifty_two_week_high)}")
    else:
        print("Can't get 52 week high")
    if fifty_two_week_low:
        print(f"52 week high: {extract_text(fifty_two_week_low)}")
    else:
        print("Can't get 52 week low")
    if fifty_day_average:
        print(f"52 week high: {extract_text(fifty_day_average)}")
    else:
        print("Can't get 50 day average")
    if two_hundred_day_average:
        print(f"200 day average: {extract_text(two_hundred_day_average)}")
    else:
        print("Can't get 200 day average")


async def main():
    await get_stock_info("2883.TW")


asyncio.run(main())
