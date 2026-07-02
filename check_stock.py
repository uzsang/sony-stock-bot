import os
import re
import json
import requests
from datetime import datetime, timedelta
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
        
        # 숫자가 아닌 문자 제거 (크기 비교용)
        clean_price = int(re.sub(r'[^0-9]', '', price_text))
        
        # 💡 [가격 데이터베이스 로직]
        history_file = 'price_history.json'
        
        # 파일이 있으면 읽어오고, 없거나 깨졌으면 빈 리스트로 시작 (자동 생성 보장)
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                try: history = json.load(f)
                except: history = []
        else:
            history = []

        # 현재 시간 기록 (UTC 기준)
        now = datetime.utcnow()
        now_str = now.strftime('%Y-%m-%d %H:%M:%S')
        
        # 💡 [수정] 필터링 조건 제거: 실행될 때마다 무조건 기록을 누적합니다.
        history.append({'timestamp': now_str, 'price': clean_price, 'text': price_text})
        
        # 💡 [수정] 보관 기간 연장: 14일(2주일)이 지난 과거 데이터만 자동으로 삭제합니다.
        fourteen_days_ago = now - timedelta(days=14)
        history = [item for item in history if datetime.strptime(item['timestamp'], '%Y-%m-%d %H:%M:%S') > fourteen_days_ago]
        
        # 데이터 정비 후 파일 저장
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
            
        # 최근 2주일간의 최저가 탐색
        if history:
            lowest_item = min(history, key=lambda x: x['price'])
            record_date = lowest_item['timestamp'][:10]
            biweekly_lowest_text = f"{lowest_item['text']}원 ({record_date} 기준)"
        else:
            biweekly_lowest_text = f"{price_text}원"
            
        # ----------------------------------------------------
        
        cron_trigger = os.environ.get('CRON_TRIGGER', '')
        is_regular_report = (cron_trigger == '0 0,12 * * *') or (cron_trigger == '')
        
        if is_regular_report:
            return [
                {"target": "regular", "text": f"📊 [정기 브리핑]\n• 현재 최저가: {price_text}원\n• 최근 2주간 최저가: {biweekly_lowest_text}"},
                {"target": "watch", "text": f"🔔 [수시 브리핑]\n• 현재 최저가: {price_text}원\n• 최근 2주간 최저가: {biweekly_lowest_text}"}
            ]
            
        return [
            {"target": "watch", "text": f"🔔 [수시 브리핑]\n• 현재 최저가: {price_text}원\n• 최근 2주간 최저가: {biweekly_lowest_text}"}
        ]
        
    except Exception as e:
        return [
            {"target": "watch", "text": f"⚠️ 가격 조회 실패. 에러 내용: {e}"}
        ]
    finally:
        driver.quit()

def send_telegram(results):
    if not results:
        return
        
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    if not chat_id:
        print("텔레그램 챗봇 ID가 누락되었습니다.")
        return
        
    for item in results:
        target = item["target"]
        text = item["text"]
        
        if target == "regular":
            token = os.environ.get('TELEGRAM_TOKEN_REGULAR')
        else:
            token = os.environ.get('TELEGRAM_TOKEN')
            
        if not token:
            print(f"[{target}] 봇 토큰이 누락되었습니다. Secrets 설정을 확인하세요.")
            continue
            
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {'chat_id': chat_id, 'text': text}
        requests.post(url, data=payload)

if __name__ == "__main__":
    results = get_lowest_price()
    send_telegram(results)
