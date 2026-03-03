import os
import requests
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# GitHub Secrets에서 정보를 가져옵니다 (보안)
TOKEN = '7831052389:AAEVBqfJRnvoxLH9R9VNt7_l6eiaRZcWuJQ'
CHAT_ID = '7639681219'

PRODUCT_LIST = [
  {"name": "RX100M7", "url": "https://store.sony.co.kr/product-view/102263765"},
  {"name": "RX100M7G", "url": "https://store.sony.co.kr/product-view/102263764"}
]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={'chat_id': CHAT_ID, 'text': message})

def check_stocks():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # GitHub Actions 환경에서의 User-Agent
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 20)
    
    available_items = []
    try:
        for product in PRODUCT_LIST:
            driver.get(product['url'])
            # 버튼 텍스트 확인 (소니스토어 구조에 맞춤)
            button_xpath = '//*[@id="root"]/div/div/div[2]/div/div[1]/form/div/div[6]/div[3]/div/ul/li[4]'
            element = wait.until(EC.presence_of_element_located((By.XPATH, button_xpath)))
            send_telegram(f"[{time.strftime('%H:%M:%S')}] {product['name']} : {element.text}")
            if "일시품절" not in element.text:
                available_items.append(product)
    finally:
        driver.quit()
    return available_items

if __name__ == "__main__":
    found = check_stocks()
    if found:
        for item in found:
            send_telegram(f"🔥 [입고!] {item['name']} 구매 가능!\n{item['url']}")
