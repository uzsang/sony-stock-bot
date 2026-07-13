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

# 범위 대역을 부드럽게 만들어주는 곡선 함수
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

def draw_graph(full_history):
    if not full_history:
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
    
    # 역대 최저가 및 날짜 추출
    all_time_min_item = min(full_history, key=lambda x: x['price'])
    all_time_min = all_time_min_item['price']
    all_time_min_date = all_time_min_item['timestamp'][:10]
    
    # 그래프에 표시할 최근 14일 데이터만 필터링
    now_kst = datetime.utcnow() + timedelta(hours=9)
    fourteen_days_ago = now_kst - timedelta(days=14)
    history = [item for item in full_history if datetime.strptime(item['timestamp'], '%Y-%m-%d %H:%M:%S') > fourteen_days_ago]
    
    colors = {"daypack": "#2563eb", "allday": "#ea580c"}
    
    daily_stats = {"daypack": {}, "allday": {}}
    for item in history:
        name = item.get('item', 'daypack')
        if name not in daily_stats:
            continue
        date_str = item['timestamp'][:10]
        price = item['price']
        
        if date_str not in daily_stats[name]:
            daily_stats[name][date_str] = {'min': price, 'max': price, 'last': price}
        else:
            daily_stats[name][date_str]['min'] = min(daily_stats[name][date_str]['min'], price)
            daily_stats[name][date_str]['max'] = max(daily_stats[name][date_str]['max'], price)
            daily_stats[name][date_str]['last'] = price

    all_prices = []
    
    for item_name, line_color in colors.items():
        if not daily_stats[item_name]:
            continue
            
        sorted_dates = sorted(daily_stats[item_name].keys())
        mins = [daily_stats[item_name][d]['min'] for d in sorted_dates]
        maxs = [daily_stats[item_name][d]['max'] for d in sorted_dates]
        lasts = [daily_stats[item_name][d]['last'] for d in sorted_dates]
        
        dates = [datetime.strptime(d, '%Y-%m-%d') for d in sorted_dates]
        dates_num = mdates.date2num(dates)
        
        all_prices.extend(maxs) 
        
        # 최저-최고 범위 부드러운 곡선 대역
        xs_smooth, ys_min_smooth = make_smooth_curve(dates_num, mins)
        _, ys_max_smooth = make_smooth_curve(dates_num, maxs)
        dates_smooth = mdates.num2date(xs_smooth)
        
        plt.fill_between(dates_smooth, ys_min_smooth, ys_max_smooth, color=line_color, alpha=0.06, edgecolor='none')
        
        # 마지막 관측 가격 메인 실선
        plt.plot(dates, lasts, marker='o', color=line_color, linewidth=1.0, 
                 markersize=4.5, markerfacecolor='#ffffff', markeredgewidth=1.0, label=item_name.upper())
        
        bbox_props = dict(boxstyle="round,pad=0.2", fc="#ffffff", ec=line_color, lw=1.0, alpha=0.8)
        
        for i, txt in enumerate(lasts):
            date_str = sorted_dates[i]
            my_price = lasts[i]
            other_item = "allday" if item_name == "daypack" else "daypack"
            
            if other_item in daily_stats and date_str in daily_stats[other_item]:
                other_price = daily_stats[other_item][date_str]['last']
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
    
    # 💡 [여백 확보] 목표가 라인과 고급화된 범례가 들어갈 공간을 확보하기 위해 상단 리미트를 늘림
    top_limit = max(y_max * 1.08, 155000)
    
    # 역대 최저가가 12만 원보다 낮을 경우 하단 범위를 자동으로 늘려 선이 보이게 조정
    bottom_limit = min(120000, all_time_min - 2000)
    plt.ylim(bottom_limit, top_limit)
    
    # 역대 최저가 진한 회색 실선
    plt.axhline(y=all_time_min, color='#475569', linestyle='-', linewidth=1.5, alpha=0.8)
    ax.text(0.02, all_time_min + 800, f'All-Time Low ({all_time_min:,} won) on {all_time_min_date}', 
            color='#475569', fontweight='bold', fontsize=9, 
            va='bottom', ha='left', transform=ax.get_yaxis_transform())
    
    # 목표가 연한 회색 점선
    target_price = 150000
    plt.axhline(y=target_price, color='#94a3b8', linestyle=':', linewidth=1.5, alpha=0.8)
    ax.text(0.02, target_price + 1000, 'Target (150,000 won)', 
            color='#94a3b8', fontweight='bold', fontsize=10, 
            va='bottom', ha='left', transform=ax.get_yaxis_transform())
    
    plt.title('Daily Final Price & Range (Recent 14 Days)', fontsize=15, fontweight='bold', pad=20, color='#1e293b')
    plt.ylabel('Price (KRW)', fontsize=10, fontweight='500', color='#64748b')
    plt.grid(axis='y', linestyle='--', color='#f1f5f9', linewidth=1.5)
    
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    
    ax.xaxis.set_major_locator(mdates.DayLocator())
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    plt.gcf().autofmt_xdate(rotation=45)
    
    ax.tick_params(colors='#64748b', labelsize=9)
    
    # 💡 [반영] 범례(Legend)를 프리미엄 UI 스타일로 세련되게 변경
    leg = plt.legend(loc='upper right', frameon=True, facecolor='#ffffff', edgecolor='#cbd5e1', 
                     fontsize=9.5, labelcolor='#334155', borderpad=0.7, handletextpad=0.6, handlelength=1.5)
    
    # 둥근 모서리 적용
    leg.get_frame().set_boxstyle("round,pad=0.5,rounding_size=0.4")
    leg.get_frame().set_linewidth(1.0)
    
    # 말풍선과 통일된 플로팅(공중에 뜬) 그림자 효과
    leg.get_frame().set_path_effects([
        pe.SimplePatchShadow(offset=(1.5, -1.5), shadow_rgbFace='#0f172a', alpha=0.06),
        pe.Normal()
    ])
    
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
            
            # 2주 최저가 비교 (메시지용)
            fourteen_days_ago = now_kst - timedelta(days=14)
            recent_item_history = [x for x in item_history if datetime.strptime(x['timestamp'], '%Y-%m-%d %H:%M:%S') > fourteen_days_ago]
            
            if recent_item_history:
                prev_lowest_item = min(recent_item_history, key=lambda x: x['price'])
                if clean_price < prev_lowest_item['price']:
                    is_new_record = True
                    new_records_triggered.append(item_name)
            
            history.append({
                'item': item_name,
                'timestamp': now_str, 
                'price': clean_price, 
                'text': price_text
            })
            
            updated_recent = [x for x in history if x.get('item', 'daypack') == item_name and datetime.strptime(x['timestamp'], '%Y-%m-%d %H:%M:%S') > fourteen_days_ago]
            lowest_item = min(updated_recent, key=lambda x: x['price'])
            
            current_results[item_name] = {
                'curr_price': clean_price,
                'low_price': lowest_item['price'],
                'buy_url': buy_url
            }
            
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
            
        # 전체 히스토리를 그래프 함수로 넘김
        graph_file = draw_graph(history)

        if new_records_triggered:
            items_str = ", ".join(new_records_triggered)
            header = f"💥💣 <b>[2주 최저가 갱신 ({items_str})!!]</b> 💣💥\n"
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
