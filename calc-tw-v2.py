import yfinance as yf
from datetime import date, timedelta
import pandas as pd
import os.path
import time
from requests_html import HTMLSession
import re

""" CHECK START """
today = date.today()
one_hundred_fifty_day = timedelta(210)
that_day = today - one_hundred_fifty_day
regex = re.compile(",")

with open("temp.txt", "r", encoding="utf-8") as ori_list:
    final_list = []

    for line in ori_list:
        stock_name = line.rstrip("\n").split(" ")[0]

        if stock_name != "0050.TW" or stock_name != "0056.TW":
            flagCheck = True

            tar = yf.Ticker(stock_name)

            try:
                # print(stock_name)

                current_price = tar.history(period="1d")["Close"][0]

                session = HTMLSession()
                url = session.get(
                    f"https://finance.yahoo.com/quote/{stock_name}/key-statistics?p={stock_name}"
                )

                fifty_two_week_high_text = url.html.find(
                    'section[data-test="qsp-statistics"] > div:nth-child(2) > div:nth-child(2) > div > div tbody tr:nth-child(4) td:nth-child(2)',
                    first=True,
                ).text
                fifty_two_week_high = float(regex.sub("", fifty_two_week_high_text))

                fifty_two_week_low_text = url.html.find(
                    'section[data-test="qsp-statistics"] > div:nth-child(2) > div:nth-child(2) > div > div tbody tr:nth-child(5) td:nth-child(2)',
                    first=True,
                ).text
                fifty_two_week_low = float(regex.sub("", fifty_two_week_low_text))

                fifty_day_average_text = url.html.find(
                    'section[data-test="qsp-statistics"] > div:nth-child(2) > div:nth-child(2) > div > div tbody tr:nth-child(6) td:nth-child(2)',
                    first=True,
                ).text
                fifty_day_average = float(regex.sub("", fifty_day_average_text))

                two_hundred_day_average_text = url.html.find(
                    'section[data-test="qsp-statistics"] > div:nth-child(2) > div:nth-child(2) > div > div tbody tr:nth-child(7) td:nth-child(2)',
                    first=True,
                ).text
                two_hundred_day_average = float(
                    regex.sub("", two_hundred_day_average_text)
                )

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
                print("{} O".format(stock_name))
                final_list.append(stock_name)
            # else:
            # print("{} X".format(stock_name))

            time.sleep(1)
ori_list.close()

path = os.path.join(os.path.dirname(__file__), ".\list")
final_file_name = os.path.join(path, "final-list-{}.txt".format(today))
with open(final_file_name, "w", encoding="utf-8") as final_file:
    final_file.write("\n".join(final_list))
final_file.close()
