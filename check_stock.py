import os
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
    # PC 버전 다나와 접속을 위해 User-Agent를 일반 PC 브라우저로 변경
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    driver = webdriver.Chrome(options=options)
    
    try:
        driver.get(url)
        wait = WebDriverWait(driver, 10)
        
        # 다나와 검색 결과 리스트에서 첫 번째 상품의 가격 요소 탐색
        # 일반적으로 다나와는 p 태그의 price_sect 클래스 하위에 strong 태그로 가격을 표시합니다.
        price_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "p.price_sect strong")))
        price_text = price_element.text
        
        return f"✅ 다나와 09J29360 현재 최저가: {price_text}원"
        
    except Exception as e:
        # 정확한 태그를 찾지 못했거나 웹페이지 로딩에 문제가 있는 경우
        return f"⚠️ 가격 조회 실패. 다나와 웹페이지 구조가 예상과 다르거나 변경되었습니다. 코드를 수정해야 합니다.\n에러 내용: {e}"
    finally:
        driver.quit()

def send_telegram(message):
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
    print(message)
    send_telegram(message)
