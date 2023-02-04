import yfinance as yf
from datetime import date

stock_name = "2330.TW"
tar = yf.Ticker(stock_name)
print(tar.info)

today = date.today()

from requests_html import HTMLSession
from bs4 import BeautifulSoup

session = HTMLSession()
url = session.get(
    f"https://finance.yahoo.com/quote/{stock_name}/key-statistics?p={stock_name}"
)
fifty_two_week_high = url.html.find(
    'section[data-test="qsp-statistics"] > div:nth-child(2) > div:nth-child(2) > div > div tbody tr:nth-child(4) td:nth-child(2)',
    first=True,
)
print(fifty_two_week_high.text)


print(tar.history(period="1d")["Close"][0])
