import os
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_lowest_price():
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
        
        price_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "p.price_sect strong")))
        price_text = price_element.text
        
        cron_trigger = os.environ.get('CRON_TRIGGER', '')
        
        # 아침 9시 / 밤 9시 정기 브리핑이거나 수동 실행일 경우
        is_regular_report = (cron_trigger == '0 0,12 * * *') or (cron_trigger == '')
        
        if is_regular_report:
            return {"target": "regular", "text": f"📊 [정기 브리핑] 09J29360 현재 최저가: {price_text}원"}
            
        # 5분 감시 주기일 경우 (조건 없이 항상 알림)
        return {"target": "watch", "text": f"🔔 [현재가 알림] 09J29360 현재 최저가: {price_text}원"}
        
    except Exception as e:
        return {"target": "watch", "text": f"⚠️ 가격 조회 실패. 에러 내용: {e}"}
    finally:
        driver.quit()

def send_telegram(result):
    if result is None:
        return
        
    # 목적지(채팅방)는 항상 회원님의 개인 ID 하나로 고정
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    # 상황에 맞춰 봇(우체부) 선택
    if result["target"] == "regular":
        token = os.environ.get('TELEGRAM_TOKEN_REGULAR')
    else:
        token = os.environ.get('TELEGRAM_TOKEN')
    
    if not token or not chat_id:
        print("텔레그램 토큰이나 챗봇 ID가 누락되었습니다. Secrets 설정을 확인하세요.")
        return
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {'chat_id': chat_id, 'text': result["text"]}
    requests.post(url, data=payload)

if __name__ == "__main__":
    result = get_lowest_price()
    send_telegram(result)
