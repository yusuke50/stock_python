import yfinance as yf
from datetime import date, timedelta
import pandas as pd
import talib


""" today = date.today()
yesterday = today - timedelta(1)
one_hundred_fifty_day = timedelta(210)
that_day = today - one_hundred_fifty_day

tsmc = yf.Ticker("2330.TW")
current_print = tsmc.info["currentPrice"]  # 收盤
two_hundred_day_average = tsmc.info["twoHundredDayAverage"]  # 200 天
fifty_day_average = tsmc.info["fiftyDayAverage"]  # 50 天
fifty_two_week_high = tsmc.info["fiftyTwoWeekHigh"]  # 52週高點
fifty_two_week_low = tsmc.info["fiftyTwoWeekLow"]  # 52週低點


historical = tsmc.history(start=that_day, end=today)
df = pd.DataFrame(historical)
one_hundred_fifty_day_average = df["Close"].mean()
last_3_row = df.tail(3)
three_day_average = last_3_row["Close"].mean() """

data = yf.download("AAPL", start="2022-03-31", end="2022-04-01", interval="1m")


def RSI(data, window=14, adjust=False):
    delta = data['Close'].diff(1).dropna()
    loss = delta.copy()
    gains = delta.copy()

    gains[gains < 0] = 0
    loss[loss > 0] = 0

    gain_ewm = gains.ewm(com=window - 1, adjust=adjust).mean()
    loss_ewm = abs(loss.ewm(com=window - 1, adjust=adjust).mean())

    RS = gain_ewm / loss_ewm
    RSI = 100 - 100 / (1 + RS)

    return RSI
