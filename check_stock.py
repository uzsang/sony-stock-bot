import os
import re
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_lowest_price():
    # 다나와 PC버전 검색결과 URL (최저가 정렬)
    url = "https://search.danawa.com/dsearch.php?query=09J29360&originalQuery=09J29360&checkedInfo=N&volumeType=allvs&page=1&limit=40&sort=priceASC&list=list&boost=true&tab=main&addDelivery=N&coupangMemberSort=&simpleDescOpen=Y&isInitTireSmartFinder=N&recommendedSort=N&defaultUICategoryCode=1832384&defaultPhysicsCategoryCode=1824%7C228109%7C228787%7C0&defaultVmTab=1&defaultVaTab=107&isZeroPrice=Y&quickProductYN=N&priceUnitSort=N&priceUnitSortOrder=A"

    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    driver = webdriver.Chrome(options=options)
    
    try:
        driver.get(url)
        wait = WebDriverWait(driver, 10)
        
        # 다나와 검색 결과 리스트에서 첫 번째 상품의 가격 요소 탐색
        price_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "p.price_sect strong")))
        price_text = price_element.text  # 예: "148,500" 또는 "152,000"
        
        # 쉼표(,) 및 숫자가 아닌 문자를 모두 제거하여 순수 숫자만 추출합니다.
        clean_price = int(re.sub(r'[^0-9]', '', price_text))
        
        # 💡 핵심 조건 추가: 15만 원 미만(150000)일 때만 메시지 생성
        if clean_price < 150000:
            return f"🚨 [가격 달성!] 09J29360 최저가가 15만 원 미만입니다!\n현재 최저가: {price_text}원"
        else:
            print(f"현재 가격이 {price_text}원이라서 15만 원 미만이 아닙니다. 알림을 건너뜁니다.")
            return None  # 15만 원 이상이면 알림을 보내지 않음
        
    except Exception as e:
        return f"⚠️ 가격 조회 실패. 에러 내용: {e}"
    finally:
        driver.quit()

def send_telegram(message):
    # message가 None이면 함수를 종료하여 텔레그램을 보내지 않습니다.
    if message is None:
        return
        
    token = os.environ.get('TELEGRAM_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        print("텔레그램 토큰이나 챗봇 ID가 설정되지 않았습니다.")
        return
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {'chat_id': chat_id, 'text': message}
    requests.post(url, data=payload)

if __name__ == "__main__":
    message = get_lowest_price()
    send_telegram(message)
