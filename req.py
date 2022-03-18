from cgi import print_directory
import requests
import re
from bs4 import BeautifulSoup

todays_list = []

res_FATCA = requests.get("https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_DD.djhtm")
items_FATCA = BeautifulSoup(res_FATCA.text, "html.parser").select("tr .t3t1 a")

for item in items_FATCA:
    re_inner = re.match(r"^(\w+)", item.decode_contents()[0:6]).group()
    todays_list.append('{}.TW'.format(re_inner))

res_main = requests.get("https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_F.djhtm")
items_main = BeautifulSoup(res_main.text, "html.parser").select("tr .t3t1 a")
for item in items_main:
    temp = re.match(r"^(\w+)", item.decode_contents()[0:6]).group()

    for l in todays_list:
        if (l != temp):
            todays_list.append('{}.TW'.format(temp))
            break

res_foreign = requests.get(
    "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_D.djhtm")
items_foreign = BeautifulSoup(
    res_foreign.text, "html.parser").select("tr .t3t1 a")
for item in items_foreign:
    temp = re.match(r"^(\w+)", item.decode_contents()[0:6]).group()

    for l in todays_list:
        if (l != temp):
            todays_list.append('{}.TW'.format(temp))
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

with open('stock-list.txt', "w", encoding="utf-8") as list_file:
    for line in lines:
        list_file.write('{}\n'.format(line))
list_file.close()
