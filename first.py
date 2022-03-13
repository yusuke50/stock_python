import twstock

stock_2330 = twstock.Stock('2330')
price_2330 = stock_2330.price[-5:]

print(price_2330)
