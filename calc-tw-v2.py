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
number_regex = re.compile(",")


def str_to_number(str):
    return float(number_regex.sub("", str))


with open("stock-list-tw.txt", "r", encoding="utf-8") as ori_list:
    final_list = []

    for line in ori_list:
        stock_name = line.rstrip("\n").split(" ")[0]

        etf_flag = True
        etf_list = ["0050.TW", "0056.TW", "0052.TW"]
        for etf in etf_list:
            if stock_name == etf:
                etf_flag = False
                break

        if etf_flag:
            flag_check = True

            tar = yf.Ticker(stock_name)

            try:
                current_price = tar.history(period="1d")["Close"][0]

                session = HTMLSession()
                url = session.get(
                    f"https://finance.yahoo.com/quote/{stock_name}/key-statistics?p={stock_name}"
                )

                fifty_two_week_high_text = url.html.find(
                    'section[data-test="qsp-statistics"] > div:nth-child(2) > div:nth-child(2) > div > div tbody tr:nth-child(4) td:nth-child(2)',
                    first=True,
                ).text
                fifty_two_week_high = str_to_number(fifty_two_week_high_text)

                fifty_two_week_low_text = url.html.find(
                    'section[data-test="qsp-statistics"] > div:nth-child(2) > div:nth-child(2) > div > div tbody tr:nth-child(5) td:nth-child(2)',
                    first=True,
                ).text
                fifty_two_week_low = str_to_number(fifty_two_week_low_text)

                fifty_day_average_text = url.html.find(
                    'section[data-test="qsp-statistics"] > div:nth-child(2) > div:nth-child(2) > div > div tbody tr:nth-child(6) td:nth-child(2)',
                    first=True,
                ).text
                fifty_day_average = str_to_number(fifty_day_average_text)

                two_hundred_day_average_text = url.html.find(
                    'section[data-test="qsp-statistics"] > div:nth-child(2) > div:nth-child(2) > div > div tbody tr:nth-child(7) td:nth-child(2)',
                    first=True,
                ).text
                two_hundred_day_average = str_to_number(two_hundred_day_average_text)

                historical = tar.history(start=that_day, end=today)
                df = pd.DataFrame(historical)
                one_hundred_fifty_day_average = df["Close"].mean()

                if current_price < one_hundred_fifty_day_average:
                    flag_check = False
                elif current_price < two_hundred_day_average:
                    flag_check = False
                elif one_hundred_fifty_day_average < two_hundred_day_average:
                    flag_check = False
                elif fifty_day_average < one_hundred_fifty_day_average:
                    flag_check = False
                elif fifty_day_average < two_hundred_day_average:
                    flag_check = False
                elif current_price < fifty_two_week_low * 1.25:
                    flag_check = False
                elif current_price < fifty_two_week_high * 0.75:
                    flag_check = False
            except KeyError as err:
                print("{} failed ({}).".format(stock_name, err))
                flag_check = False
            except IndexError as err:
                print("{} failed ({}).".format(stock_name, err))
                flag_check = False
            except AttributeError as err:
                print("{} failed ({}).".format(stock_name, err))
                flag_check = False
            except ValueError as err:
                print("{} failed ({}).".format(stock_name, err))
                flag_check = False

            if flag_check:
                # print("{} O".format(stock_name))
                final_list.append(stock_name)

            time.sleep(1)
ori_list.close()

path = os.path.join(os.path.dirname(__file__), ".\list")
final_file_name = os.path.join(path, "final-list-{}.txt".format(today))
with open(final_file_name, "w", encoding="utf-8") as final_file:
    final_file.write("\n".join(final_list))
final_file.close()
