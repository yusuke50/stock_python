from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.common.exceptions import TimeoutException


def get_stock_info(stock_name):
    options = webdriver.EdgeOptions()
    options.add_argument("--headless")
    driver = webdriver.Edge(
        service=Service(EdgeChromiumDriverManager().install()), options=options
    )

    try:
        url = f"https://finance.yahoo.com/quote/{stock_name}/key-statistics"
        driver.get(url)
        print(driver.page_source)

        wait = WebDriverWait(driver, 20)
        articles = wait.until(
            EC.presence_of_all_elements_located((By.TAG_NAME, "article"))
        )

        if len(articles) > 1:
            second_article = articles[1]

            try:
                value_element = second_article.find_element(
                    By.CSS_SELECTOR,
                    "article > div.container > section:nth-child(2) > div.column section.card:nth-child(1) .table tr:nth-child(4) .value",
                )
                value = value_element.text
                print(f"獲取的值為: {value}")
            except Exception as e:
                print(f"在第二個 article 中未找到目標元素: {e}")

        else:
            print("沒有找到足夠的 article 元素")

    except TimeoutException:
        print("頁面加載超時")
    except Exception as e:
        print(f"發生錯誤: {e}")
    finally:
        driver.quit()


get_stock_info("AAPL")
