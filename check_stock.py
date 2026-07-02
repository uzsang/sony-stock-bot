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
        
        # [가격 데이터베이스 로직]
        history_file = 'price_history.json'
        
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                try: history = json.load(f)
                except: history = []
        else:
            history = []

        # 💡 현재 시간을 한국 시간(KST)으로 계산하여 기록 (%Y-%m-%d %H:%M:%S 형식)
        now_kst = datetime.utcnow() + timedelta(hours=9)
        now_str = now_kst.strftime('%Y-%m-%d %H:%M:%S')
        
        # 실행될 때마다 무조건 기록 누적
        history.append({'timestamp': now_str, 'price': clean_price, 'text': price_text})
        
        # 14일(2주일)이 지난 과거 데이터 자동 삭제
        fourteen_days_ago = now_kst - timedelta(days=14)
        history = [item for item in history if datetime.strptime(item['timestamp'], '%Y-%m-%d %H:%M:%S') > fourteen_days_ago]
        
        # 데이터 파일 저장
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
            
        # 최근 2주일간의 최저가 및 당시 날짜/시간 탐색
        if history:
            lowest_item = min(history, key=lambda x: x['price'])
            # 💡 날짜와 시간을 모두 포함하여 표시 (예: 148,000원 (2026-07-02 17:45:00))
            biweekly_lowest_text = f"{lowest_item['text']}원 ({lowest_item['timestamp']})"
        else:
            biweekly_lowest_text = f"{price_text}원 ({now_str})"
            
        # ----------------------------------------------------
        
        cron_trigger = os.environ.get('CRON_TRIGGER', '')
        is_regular_report = (cron_trigger == '0 0,12 * * *') or (cron_trigger == '')
        
        # 💡 알림 시각(현재 시각) 항목을 추가하여 메시지 포맷 수정
        if is_regular_report:
            return [
                {"target": "regular", "text": f"📊 [정기 브리핑]\n• 알림 시각: {now_str}\n• 현재 최저가: {price_text}원\n• 최근 2주 최저가: {biweekly_lowest_text}"},
                {"target": "watch", "text": f"🔔 [수시 브리핑]\n• 알림 시각: {now_str}\n• 현재 최저가: {price_text}원\n• 최근 2주 최저가: {biweekly_lowest_text}"}
            ]
            
        return [
            {"target": "watch", "text": f"🔔 [수시 브리핑]\n• 알림 시각: {now_str}\n• 현재 최저가: {price_text}원\n• 최근 2주 최저가: {biweekly_lowest_text}"}
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
