import yfinance as yf
from datetime import date, timedelta
import pandas as pd
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
no_data_count = 0


async def process_stock(stock_name, semaphore):
    global no_data_count
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
                raise ValueError(f"Can't get stock info {stock_name}")

            fifty_two_week_high = float_convert(stock_info["fifty_two_week_high"])
            fifty_two_week_low = float_convert(stock_info["fifty_two_week_low"])
            fifty_day_average = float_convert(stock_info["fifty_day_average"])
            two_hundred_day_average = float_convert(
                stock_info["two_hundred_day_average"]
            )

            if fifty_two_week_high is None:
                no_data_count += 1
                print(f"No 52 week high data for {stock_name}, count: {no_data_count}")
            else:
                no_data_count = 0

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
                and fifty_two_week_high is not None
                and fifty_two_week_low is not None
                and one_hundred_fifty_day_average is not None
                and two_hundred_day_average is not None
                and fifty_day_average is not None
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
            return (
                None,
                f"{stock_name} (Close: {current_price if current_price is not None else 'None'}) failed ({err})",
            )

        return None, None


async def main():
    final_list = []
    err_list = []
    exception_list = []
    global no_data_count

    stock_names = ["AAPL"]

    semaphore = asyncio.Semaphore(1)
    sleep_time = 1
    long_sleep_time = 150

    async def process_with_sleep():
        global no_data_count
        process_results = []
        counter = 0
        no_data_counter = 3
        divisor = 100

        for stock in stock_names:
            if re.search(r"^00\w+\.TW$", stock):
                exception_list.append(f"{stock} (Exception)")
            else:
                result = await process_stock(stock, semaphore)
                await asyncio.sleep(sleep_time)
                process_results.append(result)
                counter += 1

                if no_data_count >= no_data_counter:
                    print(f"No data count: {no_data_count}. Pausing at stock {stock}")
                    await asyncio.sleep(long_sleep_time)
                    print(f"Resuming from stock {stock}")
                    no_data_count = 0
                    continue
                else:
                    if counter % divisor == 0:
                        print(
                            f"Processed {counter} stocks. Sleeping for {long_sleep_time} seconds..."
                        )
                        await asyncio.sleep(long_sleep_time)
        return process_results

    start_time = time.time()
    results = await process_with_sleep()
    end_time = time.time()
    print(f"Total time taken: {end_time - start_time:.2f} seconds")

    for item in results:
        if item is None:
            err_list.append("Received None from process_stock")
            continue  # Skip to the next item

        if isinstance(item, tuple) and len(item) == 2:
            result, err = item
            if result:
                final_list.append(result)
            elif err:
                if "Exception" in err:
                    exception_list.append(err)
                else:
                    err_list.append(err)
        else:
            err_list.append(f"Unexpected result: {item}")

    print(final_list)
    print(err_list)
    print(exception_list)


if __name__ == "__main__":
    asyncio.run(main())
