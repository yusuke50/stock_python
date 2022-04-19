import requests
from bs4 import BeautifulSoup

today_list = []


def getStock(type):
    url = ""
    if type == "FATCA":
        url = "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_DD.djhtm"
    elif type == "main":
        url = "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_F.djhtm"
    elif type == "foreign":
        url = "https://fubon-ebrokerdj.fbs.com.tw/Z/ZG/ZG_D.djhtm"

    items = BeautifulSoup(requests.get(url).text,
                          "html.parser").select("tr .t3t1 a")
    itemSummary = []
    for item in items:
        item = item.decode_contents().split(" ")[0]
        if len(item) == 4:
            itemSummary.append(item)
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


def check_count(item):
    f = False
    stock = ''
    count = 0

    for sl in new_file_lines:
        stock = sl.split(" ")[0][0:4]
        count = int(sl.split(" ")[1].replace("\n", ""))

        if item == stock:
            f = True
            break

    d = dict()
    d['flag'] = f
    d['count'] = count

    return d


ipt = open("stock-list-tw.txt", "r", encoding="utf-8")
new_file_lines = ipt.read().splitlines()
ipt.close()

while len(today_list) > 0:
    first_item = today_list[0]

    result = check_count(first_item)

    if result["flag"]:
        idx = new_file_lines.index(f"{first_item}.TW {result['count']}")
        new_file_lines[idx] = f"{first_item}.TW {result['count'] + 1}"
        del today_list[0]
    else:
        new_file_lines.append(f"{first_item}.TW 0")


with open("stock-list-tw.txt", "w", encoding="utf-8") as opt:
    opt.write("\n".join(new_file_lines))
opt.close()
