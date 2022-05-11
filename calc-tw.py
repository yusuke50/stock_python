import yfinance as yf
from datetime import date, timedelta
import pandas as pd
import os.path

""" CHECK START """
today = date.today()
one_hundred_fifty_day = timedelta(210)
that_day = today - one_hundred_fifty_day

with open("stock-list-tw.txt", "r", encoding="utf-8") as ori_list:
    final_list = []

    for line in ori_list:
        stock_name = line.rstrip("\n").split(" ")[0]
        flagCheck = True

        tar = yf.Ticker(stock_name)

        try:
            current_price = tar.info["currentPrice"]
            two_hundred_day_average = tar.info["twoHundredDayAverage"]
            fifty_day_average = tar.info["fiftyDayAverage"]
            fifty_two_week_high = tar.info["fiftyTwoWeekHigh"]
            fifty_two_week_low = tar.info["fiftyTwoWeekLow"]

            historical = tar.history(start=that_day, end=today)
            df = pd.DataFrame(historical)
            one_hundred_fifty_day_average = df["Close"].mean()

            if current_price < one_hundred_fifty_day_average:
                flagCheck = False
            elif current_price < two_hundred_day_average:
                flagCheck = False
            elif one_hundred_fifty_day_average < two_hundred_day_average:
                flagCheck = False
            elif fifty_day_average < one_hundred_fifty_day_average:
                flagCheck = False
            elif fifty_day_average < two_hundred_day_average:
                flagCheck = False
            elif current_price < fifty_two_week_low * 1.25:
                flagCheck = False
            elif current_price < fifty_two_week_high * 0.75:
                flagCheck = False
        except KeyError as err:
            print("{} failed ({}).".format(stock_name, err))
            flagCheck = False

        if flagCheck:
            final_list.append(stock_name)
ori_list.close()

path = os.path.join(os.path.dirname(__file__), ".\list")
final_file_name = os.path.join(path, "final-list-{}.txt".format(today))
with open(final_file_name, "w", encoding="utf-8") as final_file:
    final_file.write("\n".join(final_list))
final_file.close()
