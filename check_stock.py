import os
import re
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
        
        clean_price = int(re.sub(r'[^0-9]', '', price_text))
        cron_trigger = os.environ.get('CRON_TRIGGER', '')
        
        # 아침9시/밤9시 정시 알림이거나, 사용자가 수동(Run workflow)으로 직접 실행했을 때
        is_regular_report = (cron_trigger == '0 0,12 * * *') or (cron_trigger == '')
        
        if is_regular_report:
            # target을 'regular'방으로 설정하고 메시지 반환
            return {"target": "regular", "text": f"📊 [정기 브리핑] 09J29360 현재 최저가: {price_text}원"}
            
        # 그 외 5분마다 도는 스케줄일 때는 '15만 원 미만'일 때만 알림 전송
        if clean_price < 150000:
            # target을 'watch'(특가 감시)방으로 설정하고 메시지 반환
            return {"target": "watch", "text": f"🚨 [특가 달성!] 09J29360 최저가가 15만 원 미만입니다!\n현재 최저가: {price_text}원"}
        else:
            print(f"현재 가격이 {price_text}원이라서 알림을 건너뜁니다. (5분 주기 감시 중)")
            return None
        
    except Exception as e:
        # 에러 발생 시에는 기본 감시방으로 알림을 보냅니다.
        return {"target": "watch", "text": f"⚠️ 가격 조회 실패. 에러 내용: {e}"}
    finally:
        driver.quit()

def send_telegram(result):
    if result is None:
        return
        
    token = os.environ.get('TELEGRAM_TOKEN')
    
    # target 값에 따라 어떤 Chat ID를 쓸지 결정합니다.
    if result["target"] == "regular":
        chat_id = os.environ.get('TELEGRAM_CHAT_ID_REGULAR')
    else:
        chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        print("텔레그램 토큰이나 챗봇 ID가 설정되지 않았습니다.")
        return
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {'chat_id': chat_id, 'text': result["text"]}
    requests.post(url, data=payload)

if __name__ == "__main__":
    result = get_lowest_price()
    send_telegram(result)
