import yfinance as yf
from datetime import date, timedelta
import talib

stock_name = "2330.TW"
tar = yf.Ticker(stock_name)

today = date.today()
start_day = today - timedelta(60)

data = yf.download(stock_name, start=start_day, end=today)
windows_length = 14


def RSI(data, window=windows_length, adjust=False):
    delta = data["Close"].diff(1).dropna()
    loss = delta.copy()
    gains = delta.copy()

    gains[gains < 0] = 0
    loss[loss > 0] = 0

    gain_ewm = gains.ewm(com=window - 1, adjust=adjust).mean()
    loss_ewm = abs(loss.ewm(com=window - 1, adjust=adjust).mean())

    RS = gain_ewm / loss_ewm
    RSI = 100 - 100 / (1 + RS)

    return RSI


data["RSI"] = talib.RSI(data["Close"], 14)
print(data["RSI"].iloc[-1])

print("------------------------")

RSI_from_def = RSI(data)
print(RSI_from_def.iloc[-1])
