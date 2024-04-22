from requests_html import HTMLSession

stock_name = "3533.TW"
session = HTMLSession()
url = session.get(f"https://finance.yahoo.com/quote/{stock_name}/key-statistics")

article = url.html.find(
    "article:nth-child(1) article > div.container > section:nth-child(2) > div.column section.card:nth-child(1) .table tr:nth-child(4) .value",
    first=True,
)

print(article.text)
