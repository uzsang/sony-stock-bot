import os
import re
import json
import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
import matplotlib.patheffects as pe
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 모니터링할 아이템 이름과 다나와 주소 정의
ITEMS_INFO = {
    "daypack": "https://search.danawa.com/dsearch.php?query=09J29360&originalQuery=09J29360&checkedInfo=N&volumeType=allvs&page=1&limit=40&sort=priceASC&list=list&boost=true&tab=main&addDelivery=N&coupangMemberSort=&simpleDescOpen=Y&isInitTireSmartFinder=N&recommendedSort=N&defaultUICategoryCode=1832384&defaultPhysicsCategoryCode=1824%7C228109%7C228787%7C0&defaultVmTab=1&defaultVaTab=107&isZeroPrice=Y&quickProductYN=N&priceUnitSort=N&priceUnitSortOrder=A",
    "allday": "https://search.danawa.com/dsearch.php?query=09J09243&originalQuery=09J09243&checkedInfo=N&volumeType=allvs&page=1&limit=40&sort=priceASC&list=list&boost=true&tab=main&addDelivery=N&coupangMemberSort=N&simpleDescOpen=Y&isInitTireSmartFinder=N&recommendedSort=N&defaultUICategoryCode=13227919&defaultPhysicsCategoryCode=1825%7C9535%7C224740%7C0&defaultVmTab=2&defaultVaTab=66&isZeroPrice=Y&quickProductYN=N&priceUnitSort=N&priceUnitSortOrder=A"
}

# 💡 외부 라이브러리(scipy) 설치 없이 깃허브 액션에서 바로 작동하도록 구현한 순수 파이썬 곡선 생성 함수
def make_smooth_curve(x, y, resolution=20):
    if len(x) < 3:
        return x, y
    x_smooth, y_smooth = [], []
    for i in range(len(x) - 1):
        p0, p1, p2, p3 = max(0, i - 1), i, i + 1, min(len(x) - 1, i + 2)
        for t in range(resolution):
            t_val = t / resolution
            t2 = t_val * t_val
            t3 = t2 * t_val
            
            b0 = -t3 + 2*t2 - t_val
            b1 = 3*t3 - 5*t2 + 2
            b2 = -3*t3 + 4*t2 + t_val
            b3 = t3 - t2
            
            x_smooth.append(0.5 * (x[p0]*b0 + x[p1]*b1 + x[p2]*b2 + x[p3]*b3))
            y_smooth.append(0.5 * (y[p0]*b0 + y[p1]*b1 + y[p2]*b2 + y[p3]*b3))
    x_smooth.append(x[-1])
    y_smooth.append(y[-1])
    return x_smooth, y_smooth

def draw_graph(history):
    if not history:
        return None
        
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Helvetica Neue', 'Helvetica', 'Arial', 'Liberation Sans', 'sans-serif']
        
    plt.figure(figsize=(10, 6))
    ax = plt.gca()
    
    ax.set_facecolor('#f8f9fa')
    plt.gcf().patch.set_facecolor('#ffffff')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#e2e8f0')
    ax.spines['bottom'].set_color('#e2e8f0')
    
    colors = {"daypack": "#2563eb", "allday": "#ea580c"}
    
    all_stats = {"daypack": {}, "allday": {}}
    for item in history:
        name = item.get('item', 'daypack')
        if name not in all_stats:
            continue
        date_str = item['timestamp'][:10]
        price = item['price']
        if date_str not in all_stats[name]:
            all_stats[name][date_str] = {'min': price, 'max': price, 'last': price}
        else:
            all_stats[name][date_str]['min'] = min(all_stats[name][date_str]['min'], price)
            all_stats[name][date_str]['max'] = max(all_stats[name][date_str]['max'], price)
            all_stats[name][date_str]['last'] = price

    all_prices = []
    
    for item_name, line_color in colors.items():
        if not all_stats[item_name]:
            continue
            
        sorted_dates = sorted(all_stats[item_name].keys())
        mins = [all_stats[item_name][d]['min'] for d in sorted_dates]
        maxs = [all_stats[item_name][d]['max'] for d in sorted_dates]
        lasts = [all_stats[item_name][d]['last'] for d in sorted_dates]
        dates = [datetime.strptime(d, '%Y-%m-%d') for d in sorted_dates]
        dates_num = mdates.date2num(dates)
        
        all_prices.extend(maxs) 
        
        # 곡선 좌표 계산
        xs_smooth, ys_last_smooth = make_smooth_curve(dates_num, lasts)
        _, ys_min_smooth = make_smooth_curve(dates_num, mins)
        _, ys_max_smooth = make_smooth_curve(dates_num, maxs)
        dates_smooth = mdates.num2date(xs_smooth)
        
        # 💡 [범위] 최저-최고 범위를 직선 대신 부드러운 곡선 대역으로 칠함
        plt.fill_between(dates_smooth, ys_min_smooth, ys_max_smooth, color=line_color, alpha=0.06, edgecolor='none')
        
        # 💡 [범례용 가짜 선] 범례에 선과 마커가 모두 나오게 하기 위함
        plt.plot([], [], marker='o', color=line_color, linewidth=1.0, 
                 markersize=4.5, markerfacecolor='#ffffff', markeredgewidth=1.0, label=item_name.upper())
        
        # 💡 [메인 실선] 곡선형 추세선 그리기
        plt.plot(dates_smooth, ys_last_smooth, color=line_color, linewidth=1.0)
        
        # 💡 [마커] 실제 날짜 위치에 동그라미 포인트만 찍기
        plt.plot(dates, lasts, marker='o', color=line_color, linewidth=0, 
                 markersize=4.5, markerfacecolor='#ffffff', markeredgewidth=1.0)
        
        bbox_props = dict(boxstyle="round,pad=0.2", fc="#ffffff", ec=line_color, lw=1.0, alpha=0.8)
        
        for i, txt in enumerate(lasts):
            date_str = sorted_dates[i]
            my_price = lasts[i]
            other_item = "allday" if item_name == "daypack" else "daypack"
            
            # 겹침 방지 로직 (내가 더 비싸면 위로, 싸면 아래로)
            if other_item in all_stats and date_str in all_stats[other_item]:
                other_price = all_stats[other_item][date_str]['last']
                if my_price > other_price:
                    xy_offset = (0, 9)
                elif my_price < other_price:
                    xy_offset = (0, -16)
                else:
                    xy_offset = (0, 9) if item_name == "daypack" else (0, -16)
            else:
                xy_offset = (0, 9) if item_name == "daypack" else (0, -16)

            ann = plt.annotate(f"{txt:,} w", (dates[i], lasts[i]), 
                         textcoords="offset points", xytext=xy_offset, 
                         ha='center', fontsize=8, fontweight='700', color=line_color, alpha=0.9,
                         bbox=bbox_props)
            
            ann.get_bbox_patch().set_path_effects([
                pe.SimplePatchShadow(offset=(1.0, -1.0), shadow_rgbFace='#0f172a', alpha=0.05),
                pe.Normal()
            ])
    
    y_max = max(all_prices) if all_prices else 150000
    top_limit = max(y_max * 1.05, 125000)
    
    # 💡 [요청 사항 반영] Y축 최솟값을 120,000원으로 고정
    plt.ylim(120000, top_limit)
    
    target_price = 150000
    plt.axhline(y=target_price, color='#FF4B4B', linestyle='-', linewidth=2, alpha=0.8)
    
    ax.text(0.02, target_price + 1000, 'Target (150,000 won)', 
            color='#FF4B4B', fontweight='bold', fontsize=10, 
            va='bottom', ha='left', transform=ax.get_yaxis_transform())
    
    plt.title('Daily Lowest Price & Range (Recent 14 Days)', fontsize=15, fontweight='bold', pad=20, color='#1e293b')
    plt.ylabel('Price (KRW)', fontsize=10, fontweight='500', color='#64748b')
    plt.grid(axis='y', linestyle='--', color='#f1f5f9', linewidth=1.5)
    
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    plt.gcf().autofmt_xdate()
    
    ax.tick_params(colors='#64748b', labelsize=9)
    
    plt.legend(loc='lower right', frameon=True, facecolor='#ffffff', edgecolor='#e2e8f0', 
               fontsize=9, labelcolor='#334155', borderpad=0.8)
    
    graph_path = 'price_graph.png'
    plt.savefig(graph_path, bbox_inches='tight', dpi=150) 
    plt.close()
    
    return graph_path

def get_lowest_price():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    driver = webdriver.Chrome(options=options)
    
    history_file = 'price_history.json'
    if os.path.exists(history_file):
        with open(history_file, 'r', encoding='utf-8') as f:
            try: history = json.load(f)
            except: history = []
    else:
        history = []

    now_kst = datetime.utcnow() + timedelta(hours=9)
    now_str = now_kst.strftime('%Y-%m-%d %H:%M:%S')
    
    current_results = {}
    new_records_triggered = []
    
    try:
        for item_name, url in ITEMS_INFO.items():
            driver.get(url)
            wait = WebDriverWait(driver, 10)
            
            price_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "p.price_sect strong")))
            price_text = price_element.text
            clean_price = int(re.sub(r'[^0-9]', '', price_text))
            
            buy_url = url
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
                    buy_url = price_element.find_element(By.XPATH, "./ancestor::a").get_attribute("href")
            except:
                pass
            
            item_history = [x for x in history if x.get('item', 'daypack') == item_name]
            is_new_record = False
            if item_history:
                prev_lowest_item = min(item_history, key=lambda x: x['price'])
                if clean_price < prev_lowest_item['price']:
                    is_new_record = True
                    new_records_triggered.append(item_name)
            
            history.append({
                'item': item_name,
                'timestamp': now_str, 
                'price': clean_price, 
                'text': price_text
            })
            
            updated_item_history = [x for x in history if x.get('item', 'daypack') == item_name]
            lowest_item = min(updated_item_history, key=lambda x: x['price'])
            
            current_results[item_name] = {
                'curr_price': clean_price,
                'low_price': lowest_item['price'],
                'buy_url': buy_url
            }
            
        fourteen_days_ago = now_kst - timedelta(days=14)
        history = [item for item in history if datetime.strptime(item['timestamp'], '%Y-%m-%d %H:%M:%S') > fourteen_days_ago]
        
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
            
        graph_file = draw_graph(history)

        if new_records_triggered:
            items_str = ", ".join(new_records_triggered)
            header = f"💥💣 <b>[최저가 갱신 ({items_str})!!]</b> 💣💥\n"
        else:
            header = ""

        def format_message(title):
            time_str = now_kst.strftime('%y%m%d %H:%M')
            msg = f"{header}<b>{title}</b>\n\n"
            msg += f"알림시각 : {time_str}\n"
            msg += "상품가격(현재가/2주 최저가)\n"
            for name in ["daypack", "allday"]:
                res = current_results[name]
                msg += f"-{name.upper()} : {res['curr_price']:,} / {res['low_price']:,}\n"
            return msg.strip()
            
        cron_trigger = os.environ.get('CRON_TRIGGER', '')
        is_regular_report = (cron_trigger == '0 0,12 * * *') or (cron_trigger == '')
        
        reply_markup = {
            "inline_keyboard": [
                [{"text": "🛒 DAYPACK 최저가 바로가기", "url": current_results['daypack']['buy_url']}],
                [{"text": "🛒 ALLDAY 최저가 바로가기", "url": current_results['allday']['buy_url']}]
            ]
        }
        
        if is_regular_report:
            return [
                {"target": "regular", "text": format_message("📊 [정기 브리핑]"), "graph": graph_file, "reply_markup": reply_markup},
                {"target": "watch", "text": format_message("🔔 [수시 브리핑]"), "graph": graph_file, "reply_markup": reply_markup}
            ]
            
        return [
            {"target": "watch", "text": format_message("🔔 [수시 브리핑]"), "graph": graph_file, "reply_markup": reply_markup}
        ]
        
    except Exception as e:
        return [
            {"target": "watch", "text": f"⚠️ 가격 조회 실패.\n에러: {e}", "graph": None, "reply_markup": None}
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
        reply_markup = item.get("reply_markup")
        
        if target == "regular":
            token = os.environ.get('TELEGRAM_TOKEN_REGULAR')
        else:
            token = os.environ.get('TELEGRAM_TOKEN')
            
        if not token:
            print(f"[{target}] 봇 토큰이 누락되었습니다.")
            continue
            
        data = {
            'chat_id': chat_id,
            'caption': text,
            'parse_mode': 'HTML'
        }
        if reply_markup:
            data['reply_markup'] = json.dumps(reply_markup)
            
        if graph_file and os.path.exists(graph_file):
            url = f"https://api.telegram.org/bot{token}/sendPhoto"
            with open(graph_file, 'rb') as f:
                requests.post(url, data=data, files={'photo': f})
        else:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            data['text'] = data.pop('caption')
            requests.post(url, data=data)

if __name__ == "__main__":
    results = get_lowest_price()
    send_telegram(results)
