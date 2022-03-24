import yfinance as yf
from datetime import date, timedelta
import pandas as pd

today = date.today()
one_hundred_fifty_day = timedelta(210)
that_day = today - one_hundred_fifty_day

tsmc = yf.Ticker("2330.TW")
""" current_print = tsmc.info["currentPrice"]  # 收盤
two_hundred_day_average = tsmc.info["twoHundredDayAverage"]  # 200 天
fifty_day_average = tsmc.info["fiftyDayAverage"]  # 50 天
fifty_two_week_high = tsmc.info["fiftyTwoWeekHigh"]  # 52週高點
fifty_two_week_low = tsmc.info["fiftyTwoWeekLow"]  # 52週低點 """


historical = tsmc.history(start=that_day, end=today)
df = pd.DataFrame(historical)
one_hundred_fifty_day_average = df["Close"].mean()
