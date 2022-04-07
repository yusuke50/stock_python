from locale import windows_locale
import yfinance as yf
import talib

data = yf.download("AAPL", start="2022-03-01", end="2022-04-07")
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
