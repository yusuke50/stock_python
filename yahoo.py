import requests

""" HISTORY START """
url = "https://finance.yahoo.com/quote/2330.TW/key-statistics?p=2330.TW"
ua = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.74 Safari/537.36"}
res = requests.get(url, headers=ua)
print(res.text, file=open("test.txt", "w", encoding="utf-8"))


""" HISTORY END """

""" 
https://finance.yahoo.com/quote/2330.TW/key-statistics?p=2330.TW

https://finance.yahoo.com/quote/2330.TW/history?period1=1615992327&period2=1647528327&interval=1wk&filter=history&frequency=1wk&includeAdjustedClose=true

"""
