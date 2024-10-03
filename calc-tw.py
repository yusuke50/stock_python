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


async def process_stock(stock_name, semaphore):
    async with semaphore:
        flag_check = False
        RSI_value = 0

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

            history = tar.history()
            current_price = float_convert(history["Close"].iloc[-1])

            stock_info = await get_stock_info(stock_name)
            if stock_info is None:
                raise ValueError(f"Can't get stock info {stock_name}")

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
            RSI_value = download_data["RSI"].iloc[-1]

            if (
                current_price is not None
                and fifty_two_week_high is not None
                and fifty_two_week_low is not None
                and one_hundred_fifty_day_average is not None
                and two_hundred_day_average is not None
                and fifty_day_average is not None
                and RSI_value is not None
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
                elif RSI_value < 60:
                    flag_check = False
            else:
                flag_check = False
                raise ValueError(
                    f"Can't get stock info: {stock_name}, {current_price}, {fifty_two_week_high:.2f}, {fifty_two_week_low:.2f}, {fifty_day_average:.2f}, {one_hundred_fifty_day_average:.2f}, {two_hundred_day_average:.2f},  {RSI_value:.2f}"
                )

            if flag_check is True:
                return (
                    f"{stock_name}, Close: {current_price:.2f}, RSI(talib): {RSI_value:.2f}",
                    None,
                )

        except Exception as err:
            return None, f"{stock_name} failed ({err})"

        return None, None


async def main():
    final_list = []
    err_list = []

    with open("stock-list-tw.txt", "r", encoding="utf-8") as ori_list:
        stock_names = [line.strip() for line in ori_list]

    concurrency_limit = 5
    semaphore = asyncio.Semaphore(concurrency_limit)

    results = await asyncio.gather(
        *[process_stock(name, semaphore) for name in stock_names]
    )

    for item in results:
        if isinstance(item, tuple) and len(item) == 2:
            result, err = item
        else:
            result, err = None, f"Unexpected result: {item}"

        if result:
            final_list.append(result)
        if err:
            err_list.append(err)

    path = os.path.join(os.path.dirname(__file__), ".\\list")
    final_file_name = os.path.join(path, f"final-list-{today}.txt")
    with open(final_file_name, "w", encoding="utf-8") as final_file:
        final_file.write("--------------\n")
        final_file.write(f"{time.ctime(time.time())} TW Stock List\n")
        final_file.write("--------------\n")
        final_file.write("\n".join(final_list))
        final_file.write("\n")
        final_file.write("--------------\n")
        final_file.write("\n".join(err_list))


if __name__ == "__main__":
    asyncio.run(main())
