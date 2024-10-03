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

    article = html.find(
        "article:nth-child(1) article > div.container > section:nth-child(2) > div.column section.card:nth-child(1) .table tr:nth-child(4) .value",
        first=True,
    )

    if article:
        print(article.text)
    else:
        print("Can't get value")


async def main():
    await get_stock_info("5876.TW")


asyncio.run(main())
