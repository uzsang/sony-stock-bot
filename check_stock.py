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
    
    # 💡 [애플/구글 미니멀리즘 팔레트]
    bg_color = '#ffffff'       # 순백색 배경
    text_color = '#1d1d1f'     # 애플 특유의 진한 차콜 텍스트
    grid_color = '#e5e5ea'     # 아주 연한 회색 그리드
    line_color = '#007aff'     # 애플 샌프란시스코 블루
    target_color = '#ff3b30'   # 애플 경고 레드

    fig, ax = plt.subplots(figsize=(10, 5), facecolor=bg_color)
    ax.set_facecolor(bg_color)
    
    # 불필요한 사방 테두리 완벽히 제거
    for spine in ax.spines.values():
        spine.set_visible(False)
    
    # 세로선 없이 가로선만 얇고 연하게 배치 (데이터를 방해하지 않음)
    ax.grid(axis='y', color=grid_color, linestyle='-', linewidth=1)
    ax.set_axisbelow(True)
    
    # 눈금(Tick) 튀어나온 선 제거, 글자 색상 은은하게 처리
    ax.tick_params(axis='both', which='both', length=0, labelsize=10, colors='#86868b')
    
    # 매우 굵고 선명한 메인 라인 (끝부분을 둥글게 처리하여 세련미 강조)
    plt.plot(dates, sorted_prices, color=line_color, linewidth=4, solid_capstyle='round')
    
    # 포인트 마커: 크고 깔끔한 흰색 바탕에 파란 테두리
    plt.plot(dates, sorted_prices, 'o', color=line_color, markersize=9, markerfacecolor='#ffffff', markeredgewidth=2.5)
    
    y_max = max(sorted_prices)
    top_limit = max(y_max * 1.05, 155000)
    plt.ylim(100000, top_limit)
    
    # 바닥면 채우기 (아주 옅은 블루로 여백의 미 강조)
    plt.fill_between(dates, sorted_prices, 100000, color=line_color, alpha=0.04)
    
    # 목표가 선: 심플한 점선
    target_price = 150000
    plt.axhline(y=target_price, color=target_color, linestyle='--', linewidth=1.5, dashes=(4, 4))
    plt.text(dates[0], target_price + 1200, ' Target 150,000', color=target_color, fontweight='bold', fontsize=10, va='bottom')
    
    # 미니멀리즘을 위해 'won'을 제거하고 심플하게 콤마 숫자만 표시
    for i, txt in enumerate(sorted_prices):
        plt.annotate(f"{txt:,}", (dates[i], sorted_prices[i]), 
                     textcoords="offset points", xytext=(0, 14), 
                     ha='center', fontsize=11, fontweight='bold', color=text_color)
    
    # 발표 화면처럼 여백이 있는 크고 깔끔한 좌측 정렬 타이틀
    plt.title('Price Trend', fontsize=20, fontweight='bold', pad=25, color=text_color, loc='left')
    
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    # 날짜도 심플하게 슬래시(/) 형태 사용 (예: 07/02)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    plt.xticks(dates)
    
    # 레이아웃 여백 자동 최적화
    plt.tight_layout()
    
    graph_path = 'price_graph.png'
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
