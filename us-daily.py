import yfinance as yf
from datetime import date, timedelta
import pandas as pd
import os.path
import time
import re
import talib
import numpy as np
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

        try:
            flag_check = False
            RSI_value = 0
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

            try:
                history = tar.history()
            except:
                history = None
                print(f"IndexError: Unable to access the history for {stock_name}.")

            try:
                current_price = float_convert(history["Close"].iloc[-1])
            except:
                current_price = None
                print(
                    f"IndexError: Unable to access the current price for {stock_name}."
                )

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

            download_data = yf.download(
                stock_name, start=sixty_day, end=today, auto_adjust=True
            )
            close_prices = download_data["Close"].values
            download_data["RSI"] = talib.RSI(np.ravel(close_prices), 14)
            try:
                RSI_value = download_data["RSI"].iloc[-1]
            except:
                RSI_value = None
                print(
                    f"IndexError: Unable to access the last RSI value for {stock_name}."
                )

            if (
                current_price is not None
                and fifty_day_average is not None
                and one_hundred_fifty_day_average is not None
                and two_hundred_day_average is not None
                and fifty_two_week_high is not None
                and fifty_two_week_low is not None
                and RSI_value is not None
            ):
                flag_check = True
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
                    f"Can't get stock info: {stock_name}, "
                    f"Current Price: {current_price if current_price is not None else 'None'}, "
                    f"52 Week High: {fifty_two_week_high if fifty_two_week_high is not None else 'None'}, "
                    f"52 Week Low: {fifty_two_week_low if fifty_two_week_low is not None else 'None'}, "
                    f"50 Day Average: {fifty_day_average if fifty_day_average is not None else 'None'}, "
                    f"150 Day Average: {one_hundred_fifty_day_average if one_hundred_fifty_day_average is not None else 'None'}, "
                    f"200 Day Average: {two_hundred_day_average if two_hundred_day_average is not None else 'None'}, "
                    f"RSI: {RSI_value if RSI_value is not None else 'None'}"
                )

            if flag_check is True:
                return (
                    f"{stock_name}, Close: {current_price:.2f}, RSI(talib): {RSI_value:.2f}",
                    None,
                )

        except Exception as err:
            return None, f"{stock_name} failed ({err})."

        return None, None


async def main():
    final_list = []
    err_list = []

    with open("stock-list-us.txt", "r") as ori_list:
        stock_names = [line.strip() for line in ori_list]

    concurrency_limit = 3
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
    final_file_name = os.path.join(path, f"us-final-list-{today}.txt")
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
