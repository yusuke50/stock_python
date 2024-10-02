import yfinance as yf
from datetime import date, timedelta
import pandas as pd
import os.path
import time
from requests_html import HTMLSession
import re
import talib
from yf_parser_module import get_stock_info
import asyncio

""" CHECK START """
today = date.today()
one_hundred_fifty_day = timedelta(210)
that_day = today - one_hundred_fifty_day
sixty_day = today - timedelta(60)
number_regex = re.compile(",")


def str_to_number(str):
    return float(number_regex.sub("", str))


async def process_stock(stock_name, semaphore):
    async with semaphore:
        flag_check = True
        RSI_value_1 = 0
        RSI_value_2 = 0

        try:
            tar = yf.Ticker(stock_name)

            def float_convert(value):
                if value is None:
                    return None

                try:
                    if isinstance(value, (int, float)):
                        return float(value)
                    elif isinstance(value, str):
                        return float(value.replace(",", ""))
                except (ValueError, TypeError):
                    print(f"Can't convert {value} to float (stock: {stock_name})")
                    return None

            current_price = float_convert(tar.history(period="1d")["Close"].iloc[0])

            stock_info = await get_stock_info(stock_name)
            if stock_info is None:
                raise ValueError("Can't get stock info")

            fifty_two_week_high = float_convert(stock_info["fifty_two_week_high"])
            fifty_two_week_low = float_convert(stock_info["fifty_two_week_low"])
            fifty_day_average = float_convert(stock_info["fifty_day_average"])
            two_hundred_day_average = float_convert(
                stock_info["two_hundred_day_average"]
            )

            historical = tar.history(start=that_day, end=today)
            df = pd.DataFrame(historical)
            one_hundred_fifty_day_average = float_convert(df["Close"].mean())

            download_data = yf.download(stock_name, start=sixty_day, end=today)
            download_data["RSI"] = talib.RSI(download_data["Close"], 14)
            RSI_value_1 = download_data["RSI"].iloc[-1]

            print(
                stock_name,
                current_price,
                fifty_day_average,
                one_hundred_fifty_day_average,
                two_hundred_day_average,
                fifty_two_week_high,
                fifty_two_week_low,
            )

            if (
                current_price is not None
                and fifty_day_average is not None
                and one_hundred_fifty_day_average is not None
                and two_hundred_day_average is not None
                and fifty_two_week_high is not None
                and fifty_two_week_low is not None
                and RSI_value_1 is not None
            ):
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
                elif RSI_value_1 < 60:
                    flag_check = False

            if flag_check:
                return f"{stock_name}, RSI(talib): {RSI_value_1}", None

        except Exception as err:
            return None, f"{stock_name} failed ({err})."

        return None, None


async def main():
    final_list = []
    err_list = []

    with open("stock-list-us.txt", "r") as ori_list:
        stock_names = [line.strip() for line in ori_list]

    concurrency_limit = 5
    semaphore = asyncio.Semaphore(concurrency_limit)

    results = await asyncio.gather(
        *[process_stock(name, semaphore) for name in stock_names]
    )

    for result, err in results:
        if result:
            final_list.append(result)
        if err:
            err_list.append(err)

    path = os.path.join(os.path.dirname(__file__), ".\\us-list")
    final_file_name = os.path.join(path, f"us-final-list-{date.today()}.txt")
    with open(final_file_name, "w", encoding="utf-8") as final_file:
        final_file.write("--------------\n")
        final_file.write(f"{time.ctime(time.time())} US Stock List\n")
        final_file.write("--------------\n")
        final_file.write("\n".join(final_list))
        final_file.write("\n")
        final_file.write("--------------\n")
        final_file.write("\n".join(err_list))


if __name__ == "__main__":
    asyncio.run(main())
