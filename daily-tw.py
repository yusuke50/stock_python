import requests
import re
from bs4 import BeautifulSoup
import yfinance as yf
from datetime import date, timedelta
import pandas as pd

""" LIST START """
todays_list = []

res_FATCA = requests.get("https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_DD.djhtm")
items_FATCA = BeautifulSoup(res_FATCA.text, "html.parser").select("tr .t3t1 a")

for item in items_FATCA:
    re_inner = re.match(r"^(\w+)", item.decode_contents()[0:6]).group()
    todays_list.append("{}.TW".format(re_inner))

res_main = requests.get("https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_F.djhtm")
items_main = BeautifulSoup(res_main.text, "html.parser").select("tr .t3t1 a")
for item in items_main:
    temp = re.match(r"^(\w+)", item.decode_contents()[0:6]).group()

    for l in todays_list:
        if (l != temp):
            todays_list.append("{}.TW".format(temp))
            break

res_foreign = requests.get(
    "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_D.djhtm")
items_foreign = BeautifulSoup(
    res_foreign.text, "html.parser").select("tr .t3t1 a")
for item in items_foreign:
    temp = re.match(r"^(\w+)", item.decode_contents()[0:6]).group()

    for l in todays_list:
        if (l != temp):
            todays_list.append("{}.TW".format(temp))
            break

ori_file = open("stock-list.txt", "r", encoding="utf-8")
lines = ori_file.read().splitlines()
ori_file.close()

for item in todays_list:
    flag = False

    for line in lines:
        if (line == item):
            flag = True
            break

    if (not flag):
        lines.append(item)

with open("stock-list.txt", "w", encoding="utf-8") as list_file:
    for line in lines:
        list_file.write("{}\n".format(line))
list_file.close()
""" LIST END """

""" CHECK START """
today = date.today()
one_hundred_fifty_day = timedelta(210)
that_day = today - one_hundred_fifty_day

first_list = open("stock-list.txt", "r", encoding="utf-8")
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
        break
    elif current_price < two_hundred_day_average:
        flag = False
        break
    elif one_hundred_fifty_day_average < two_hundred_day_average:
        flag = False
        break
    elif fifty_day_average < one_hundred_fifty_day_average:
        flag = False
        break
    elif fifty_day_average < two_hundred_day_average:
        flag = False
        break
    elif current_price < fifty_two_week_low * 1.25:
        flag = False
        break
    elif current_price < fifty_two_week_high * 0.75:
        flag = False
        break

    if (flag):
        final_list.append(line)

final_file_name = ("final-list-{}.txt").format(today)
with open(final_file_name, "w", encoding="utf-8") as final_file:
    for line in final_list:
        final_file.write("{}\n".format(line))
final_file.close()
