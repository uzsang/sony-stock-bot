import os
import re
import json
import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

TARGET_URL = "https://search.danawa.com/dsearch.php?query=09J29360&originalQuery=09J29360&checkedInfo=N&volumeType=allvs&page=1&limit=40&sort=priceASC&list=list&boost=true&tab=main&addDelivery=N&coupangMemberSort=&simpleDescOpen=Y&isInitTireSmartFinder=N&recommendedSort=N&defaultUICategoryCode=1832384&defaultPhysicsCategoryCode=1824%7C228109%7C228787%7C0&defaultVmTab=1&defaultVaTab=107&isZeroPrice=Y&quickProductYN=N&priceUnitSort=N&priceUnitSortOrder=A"

# 💡 그래프를 그리고 이미지 파일로 저장하는 함수
def draw_graph(history):
    if not history:
        return None
        
    times = [datetime.strptime(item['timestamp'], '%Y-%m-%d %H:%M:%S') for item in history]
    prices = [item['price'] for item in history]
    
    plt.figure(figsize=(8, 4))
    plt.plot(times, prices, marker='o', color='#FF4B4B', linestyle='-', markersize=4)
    plt.title('Price Trend (Recent 14 Days)', fontsize=12, fontweight='bold')
    plt.xlabel('Date', fontsize=10)
    plt.ylabel('Price (KRW)', fontsize=10)
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # X축 날짜 포맷 깔끔하게 정리 (월-일 형태)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    plt.gcf().autofmt_xdate()
    
    graph_path = 'price_graph.png'
    plt.savefig(graph_path, bbox_inches='tight')
    plt.close()
    
    return graph_path

def get_lowest_price():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    driver = webdriver.Chrome(options=options)
    
    try:
        driver.get(TARGET_URL)
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

        # 그래프 생성 (저장된 이미지 경로 반환)
        graph_file = draw_graph(history)

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
                {"target": "regular", "text": format_message("📊 [정기 브리핑]"), "graph": graph_file},
                {"target": "watch", "text": format_message("🔔 [수시 브리핑]"), "graph": graph_file}
            ]
            
        return [
            {"target": "watch", "text": format_message("🔔 [수시 브리핑]"), "graph": graph_file}
        ]
        
    except Exception as e:
        return [
            {"target": "watch", "text": f"⚠️ 가격 조회 실패.\n에러: {e}", "graph": None}
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
        
    # 💡 [버튼 디자인] Inline Keyboard 설정 (다나와 구매 링크)
    reply_markup = {
        "inline_keyboard": [
            [{"text": "🛒 다나와 구매하러 가기", "url": TARGET_URL}]
        ]
    }
        
    for item in results:
        target = item["target"]
        text = item["text"]
        graph_file = item.get("graph")
        
        if target == "regular":
            token = os.environ.get('TELEGRAM_TOKEN_REGULAR')
        else:
            token = os.environ.get('TELEGRAM_TOKEN')
            
        if not token:
            print(f"[{target}] 봇 토큰이 누락되었습니다.")
            continue
            
        # 그래프 파일이 있으면 사진 전송 API(sendPhoto)를 사용하고, 텍스트는 캡션(caption)에 넣습니다.
        if graph_file and os.path.exists(graph_file):
            url = f"https://api.telegram.org/bot{token}/sendPhoto"
            data = {
                'chat_id': chat_id,
                'caption': text,
                'parse_mode': 'HTML',
                'reply_markup': json.dumps(reply_markup) # 💡 버튼 데이터 첨부
            }
            with open(graph_file, 'rb') as f:
                requests.post(url, data=data, files={'photo': f})
        else:
            # 그래프가 없을 경우 기존처럼 텍스트만 전송 (버튼은 동일하게 첨부)
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'HTML',
                'reply_markup': json.dumps(reply_markup)
            }
            requests.post(url, data=data)

if __name__ == "__main__":
    results = get_lowest_price()
    send_telegram(results)
