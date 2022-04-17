import yfinance as yf
from datetime import date, timedelta
import pandas as pd

""" CHECK START """
today = date.today()
one_hundred_fifty_day = timedelta(210)
that_day = today - one_hundred_fifty_day

first_list = open("stock-list-us.txt", "r")
first_lines = first_list.read().splitlines()
first_list.close()

final_list = []

for line in first_lines:
    flag = True

    tar = yf.Ticker(line)
    current_price = tar.info["currentPrice"]
    two_hundred_day_average = tar.info["twoHundredDayAverage"]
    fifty_day_average = tar.info["fiftyDayAverage"]
    fifty_two_week_high = tar.info["fiftyTwoWeekHigh"]
    fifty_two_week_low = tar.info["fiftyTwoWeekLow"]

    historical = tar.history(start=that_day, end=today)
    df = pd.DataFrame(historical)
    one_hundred_fifty_day_average = df["Close"].mean()

    if current_price < one_hundred_fifty_day_average:
        flag = False
    elif current_price < two_hundred_day_average:
        flag = False
    elif one_hundred_fifty_day_average < two_hundred_day_average:
        flag = False
    elif fifty_day_average < one_hundred_fifty_day_average:
        flag = False
    elif fifty_day_average < two_hundred_day_average:
        flag = False
    elif current_price < fifty_two_week_low * 1.25:
        flag = False
    elif current_price < fifty_two_week_high * 0.75:
        flag = False

    if flag:
        final_list.append(line)

final_file_name = ("final-list-us-{}.txt").format(today)
with open(final_file_name, "w", encoding="utf-8") as final_file:
    for line in final_list:
        final_file.write("{}\n".format(line))
final_file.close()
