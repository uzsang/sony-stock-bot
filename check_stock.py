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

# 💡 모바일 화면에서 한글과 영문/숫자의 폭을 계산하여 표 테두리를 고정하는 함수
def pad_text(text, width):
    current_width = 0
    for char in text:
        # 한글 범위 체크 (한글은 2칸, 나머지는 1칸 차지)
        if '\uac00' <= char <= '\ud7a3' or '\u1100' <= char <= '\u11ff' or '\u3130' <= char <= '\u318f':
            current_width += 2
        else:
            current_width += 1
    return text + ' ' * (width - current_width)

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

        # 💡 [ㄱ, └ 형태로 사방을 닫은 완성형 표 디자인]
        def format_message(title):
            col1 = 9  # 왼쪽 항목 컬럼 너비
            col2 = 14 # 오른쪽 상세정보 컬럼 너비
            
            sep_top = "┌" + "─" * col1 + "┬" + "─" * col2 + "┐"
            sep_mid = "├" + "─" * col1 + "┼" + "─" * col2 + "┤"
            sep_bot = "└" + "─" * col1 + "┴" + "─" * col2 + "┘"
            
            r_head = f"│{pad_text('   항목', col1)}│{pad_text(' 상세정보', col2)}│"
            r_curr = f"│{pad_text('  현재가', col1)}│{pad_text(f' {price_text}원', col2)}│"
            r_date = f"│{pad_text('  시각', col1)}│{pad_text(f' {current_date}', col2)}│"
            r_time = f"│{pad_text('', col1)}│{pad_text(f' {current_time}', col2)}│"
            r_low  = f"│{pad_text('  2주최저', col1)}│{pad_text(f' {lowest_price_str}원', col2)}│"
            r_ldat = f"│{pad_text('  기록일', col1)}│{pad_text(f' {lowest_date}', col2)}│"
            r_ltim = f"│{pad_text('  기록시', col1)}│{pad_text(f' {lowest_time}', col2)}│"
            
            return f"""<b>{title}</b>
<code>
{sep_top}
{r_head}
{sep_mid}
{r_curr}
{r_date}
{r_time}
{sep_mid}
{r_low}
{r_ldat}
{r_ltim}
{sep_bot}
</code>"""
            
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
    if not Jack or not results:
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
