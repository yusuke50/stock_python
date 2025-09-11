from requests_html import HTMLSession
import re
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

today_list = []


def getStock(type):
    url = ""
    if type == "FATCA":
        url = "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_DD.djhtm"
    elif type == "main":
        url = "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_F.djhtm"
    elif type == "foreign":
        url = "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_D.djhtm"

    session = HTMLSession()
    datahtml = session.get(url, verify=False)
    items = datahtml.html.find("tr .t3t1 a")

    itemSummary = []
    for item in items:
        regexr = r"([A-Z0-9a-z]{4,})"
        match = re.match(regexr, item.text)
        itemSummary.append(match.group(0))
    return itemSummary


def check_item(item):
    f = False

    for tl in today_list:
        if item == tl:
            f = True
            break

    return f


def check_list_len(list):
    while len(list) > 0:
        first_item = list[0]
        flag = check_item(first_item)
        if flag:
            del list[0]
        else:
            today_list.append(first_item)


fatca_list = getStock("FATCA")
today_list = fatca_list
main_list = getStock("main")
check_list_len(main_list)
foreign_list = getStock("foreign")
check_list_len(foreign_list)


def check_list(item):
    f = False
    stock = ""

    for sl in new_file_lines:
        stock = sl.split(".TW")[0]

        if item == stock:
            f = True
            break

    d = dict()
    d["flag"] = f

    return d


ipt = open("stock-list-tw.txt", "r", encoding="utf-8")
new_file_lines = ipt.read().splitlines()
ipt.close()

while len(today_list) > 0:
    first_item = today_list[0]
    result = check_list(first_item)

    if result["flag"] is False:
        new_file_lines.append(f"{first_item}.TW")
    del today_list[0]


with open("stock-list-tw.txt", "w", encoding="utf-8") as opt:
    opt.write("\n".join(new_file_lines))
opt.close()
