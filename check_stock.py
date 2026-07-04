import os
import re
import json
import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

TARGET_URL = "https://search.danawa.com/dsearch.php?query=09J29360&originalQuery=09J29360&checkedInfo=N&volumeType=allvs&page=1&limit=40&sort=priceASC&list=list&boost=true&tab=main&addDelivery=N&coupangMemberSort=&simpleDescOpen=Y&isInitTireSmartFinder=N&recommendedSort=N&defaultUICategoryCode=1832384&defaultPhysicsCategoryCode=1824%7C228109%7C228787%7C0&defaultVmTab=1&defaultVaTab=107&isZeroPrice=Y&quickProductYN=N&priceUnitSort=N&priceUnitSortOrder=A"

def draw_graph(history):
    if not history:
        return None
        
    daily_min = {}
    for item in history:
        date_str = item['timestamp'][:10]
        price = item['price']
        
        if date_str not in daily_min or price < daily_min[date_str]:
            daily_min[date_str] = price
            
    sorted_dates = sorted(daily_min.keys())
    sorted_prices = [daily_min[d] for d in sorted_dates]
    dates = [datetime.strptime(d, '%Y-%m-%d') for d in sorted_dates]
    
    # 💡 [프리미엄 다크 모드 색상 팔레트]
    bg_color = '#18181b'       # 전체 배경색 (고급스러운 다크 그레이)
    panel_color = '#27272a'    # 패널 색상
    text_color = '#e4e4e7'     # 텍스트 색상 (밝은 회색)
    grid_color = '#3f3f46'     # 그리드 선 색상
    line_color = '#22d3ee'     # 메인 그래프 선 (네온 시안)
    target_color = '#f43f5e'   # 목표가 선 (네온 로즈/레드)

    plt.figure(figsize=(10, 5), facecolor=bg_color)
    ax = plt.gca()
    ax.set_facecolor(bg_color)
    
    # 테두리 제거 (모던한 느낌)
    for spine in ax.spines.values():
        spine.set_visible(False)
    
    # 가로 그리드 은은하게 추가
    plt.grid(axis='y', color=grid_color, linestyle='--', linewidth=0.7, alpha=0.5)
    
    # 💡 선에 은은하게 빛나는 글로우(Glow) 효과 주기
    for n in range(1, 4):
        plt.plot(dates, sorted_prices, marker='', color=line_color, linewidth=2+(n*2), alpha=0.1)
        
    # 메인 라인 그리기
    plt.plot(dates, sorted_prices, marker='o', color=line_color, linewidth=2.5, 
             markersize=7, markerfacecolor=bg_color, markeredgecolor=line_color, markeredgewidth=2.5)
    
    y_max = max(sorted_prices)
    top_limit = max(y_max * 1.05, 155000)
    plt.ylim(100000, top_limit)
    
    # 선 아래쪽 은은한 그라데이션(투명도) 채우기
    plt.fill_between(dates, sorted_prices, 100000, color=line_color, alpha=0.08)
    
    # 목표가 빨간 실선 (세련된 레드)
    target_price = 150000
    plt.axhline(y=target_price, color=target_color, linestyle='-', linewidth=1.5, alpha=0.8)
    # 목표가 텍스트 위치 및 스타일 조정
    plt.text(dates[0], target_price + 1500, ' TARGET (150,000 won)', color=target_color, fontweight='900', fontsize=10)
    
    # 💡 가격 텍스트를 말풍선(Badge) 스타일로 예쁘게 표시
    for i, txt in enumerate(sorted_prices):
        bbox_props = dict(boxstyle="round,pad=0.4", fc=panel_color, ec=grid_color, lw=1, alpha=0.9)
        plt.annotate(f"{txt:,} won", (dates[i], sorted_prices[i]), 
                     textcoords="offset points", xytext=(0, 15), 
                     ha='center', fontsize=9, fontweight='bold', color=text_color, bbox=bbox_props)
    
    # 타이틀 및 축 폰트 색상 다크모드에 맞게 변경
    plt.title('Daily Lowest Price (Recent 14 Days)', fontsize=15, fontweight='900', pad=20, color='#ffffff', loc='left')
    
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    
    # X축, Y축 눈금 색상 변경
    ax.tick_params(colors=text_color, which='both')
    plt.xticks(dates, rotation=45)
    
    graph_path = 'price_graph.png'
    # 고화질(dpi=200)로 저장하여 모바일 확대 시에도 깨지지 않게 설정
    plt.savefig(graph_path, bbox_inches='tight', dpi=200, facecolor=bg_color) 
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
        
        buy_url = TARGET_URL
        
        try:
            li_parent = price_element.find_element(By.XPATH, "./ancestor::li[1]")
            try:
                link_el = li_parent.find_element(By.CSS_SELECTOR, ".prod_pricelist li:first-child a")
                extracted_url = link_el.get_attribute("href")
                if extracted_url and "javascript" not in extracted_url:
                    buy_url = extracted_url
                else:
                    buy_url = price_element.find_element(By.XPATH, "./ancestor::a").get_attribute("href")
            except:
                try:
                    buy_url = price_element.find_element(By.XPATH, "./ancestor::a").get_attribute("href")
                except:
                    pass
        except Exception as e:
            pass
        
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
        
        history.append({
            'timestamp': now_str, 
            'price': clean_price, 
            'text': price_text
        })
        
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
                {"target": "regular", "text": format_message("📊 [정기 브리핑]"), "graph": graph_file, "buy_url": buy_url},
                {"target": "watch", "text": format_message("🔔 [수시 브리핑]"), "graph": graph_file, "buy_url": buy_url}
            ]
            
        return [
            {"target": "watch", "text": format_message("🔔 [수시 브리핑]"), "graph": graph_file, "buy_url": buy_url}
        ]
        
    except Exception as e:
        return [
            {"target": "watch", "text": f"⚠️ 가격 조회 실패.\n에러: {e}", "graph": None, "buy_url": TARGET_URL}
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
        graph_file = item.get("graph")
        buy_url = item.get("buy_url", TARGET_URL)
        
        reply_markup = {
            "inline_keyboard": [
                [{"text": "🛒 최저가 판매처로 바로가기", "url": buy_url}]
            ]
        }
        
        if target == "regular":
            token = os.environ.get('TELEGRAM_TOKEN_REGULAR')
        else:
            token = os.environ.get('TELEGRAM_TOKEN')
            
        if not token:
            print(f"[{target}] 봇 토큰이 누락되었습니다.")
            continue
            
        if graph_file and os.path.exists(graph_file):
            url = f"https://api.telegram.org/bot{token}/sendPhoto"
            data = {
                'chat_id': chat_id,
                'caption': text,
                'parse_mode': 'HTML',
                'reply_markup': json.dumps(reply_markup) 
            }
            with open(graph_file, 'rb') as f:
                requests.post(url, data=data, files={'photo': f})
        else:
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
