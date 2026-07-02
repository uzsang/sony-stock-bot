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
        
        clean_price = int(re.sub(r'[^0-9]', '', price_text))
        
        history_file = 'price_history.json'
        
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                try: history = json.load(f)
                except: history = []
        else:
            history = []

        # 💡 [신규 로직] 현재 가격을 기록하기 전에, 이전 2주 기록과 비교하여 최저가 갱신 여부 확인
        is_new_record = False
        if history:
            prev_lowest_item = min(history, key=lambda x: x['price'])
            if clean_price < prev_lowest_item['price']:
                is_new_record = True

        now_kst = datetime.utcnow() + timedelta(hours=9)
        now_str = now_kst.strftime('%Y-%m-%d %H:%M:%S')
        
        current_date = now_kst.strftime('%Y-%m-%d')
        current_time = now_kst.strftime('%H:%M:%S')
        
        history.append({'timestamp': now_str, 'price': clean_price, 'text': price_text})
        
        fourteen_days_ago = now_kst - timedelta(days=14)
        history = [item for item in history if datetime.strptime(item['timestamp'], '%Y-%m-%d %H:%M:%S') > fourteen_days_ago]
        
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
            
        if history:
            lowest_item = min(history, key=lambda x: x['price'])
            lowest_price_str = lowest_item['text']
            lowest_date = lowest_item['timestamp'][:10]
            lowest_time = lowest_item['timestamp'][11:]
        else:
            lowest_price_str = price_text
            lowest_date = current_date
            lowest_time = current_time

        # 💡 [디자인] 최저가 갱신 시 폭탄이 터지는 강렬한 헤더 추가
        def format_message(title):
            if is_new_record:
                header = f"💥💣 <b>[역대급 최저가 갱신!!]</b> 💣💥\n<b>{title}</b>"
            else:
                header = f"<b>{title}</b>"

            return f"""{header}
───────────
⏰ <b>알림 시각</b>
  {current_date}
  {current_time}
───────────
💰 <b>현재 최저가</b>
  {price_text}원
───────────
📉 <b>2주 최저가</b>
  {lowest_price_str}원
  ({lowest_date})
  ({lowest_time})
───────────"""
            
        cron_trigger = os.environ.get('CRON_TRIGGER', '')
        is_regular_report = (cron_trigger == '0 0,12 * * *') or (cron_trigger == '')
        
        if is_regular_report:
            return [
                {"target": "regular", "text": format_message("📊 [정기 브리핑]")},
                {"target": "watch", "text": format_message("🔔 [수시 브리핑]")}
            ]
            
        return [
            {"target": "watch", "text": format_message("🔔 [수시 브리핑]")}
        ]
        
    except Exception as e:
        return [
            {"target": "watch", "text": f"⚠️ 가격 조회 실패.\n에러: {e}"}
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
        payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
        requests.post(url, data=payload)

if __name__ == "__main__":
    results = get_lowest_price()
    send_telegram(results)
