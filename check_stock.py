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

# 모니터링할 3개의 아이템 이름과 다나와 주소 정의
ITEMS_INFO = {
    "daypack": "https://search.danawa.com/dsearch.php?query=09J29360&originalQuery=09J29360&checkedInfo=N&volumeType=allvs&page=1&limit=40&sort=priceASC&list=list&boost=true&tab=main&addDelivery=N&coupangMemberSort=&simpleDescOpen=Y&isInitTireSmartFinder=N&recommendedSort=N&defaultUICategoryCode=1832384&defaultPhysicsCategoryCode=1824%7C228109%7C228787%7C0&defaultVmTab=1&defaultVaTab=107&isZeroPrice=Y&quickProductYN=N&priceUnitSort=N&priceUnitSortOrder=A",
    "allday": "https://search.danawa.com/dsearch.php?query=09J09243&originalQuery=09J09243&checkedInfo=N&volumeType=allvs&page=1&limit=40&sort=priceASC&list=list&boost=true&tab=main&addDelivery=N&coupangMemberSort=N&simpleDescOpen=Y&isInitTireSmartFinder=N&recommendedSort=N&defaultUICategoryCode=13227919&defaultPhysicsCategoryCode=1825%7C9535%7C224740%7C0&defaultVmTab=2&defaultVaTab=66&isZeroPrice=Y&quickProductYN=N&priceUnitSort=N&priceUnitSortOrder=A",
    "daynhalf": "https://search.danawa.com/dsearch.php?query=09J29453&originalQuery=09J29453&checkedInfo=N&volumeType=allvs&page=1&limit=40&sort=priceASC&list=list&boost=true&tab=main&addDelivery=N"
}

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
    
    # 역대 최저가 및 날짜 추출 (그래프 스케일을 위해 1000으로 나눔)
    all_time_min_item = min(full_history, key=lambda x: x['price'])
    all_time_min = all_time_min_item['price'] / 1000.0
    all_time_min_date = all_time_min_item['timestamp'][:10]
    
    # 그래프에 표시할 최근 3주(21일) 데이터만 필터링
    now_kst = datetime.utcnow() + timedelta(hours=9)
    target_days_ago = now_kst - timedelta(days=21)
    history = [item for item in full_history if datetime.strptime(item['timestamp'], '%Y-%m-%d %H:%M:%S') > target_days_ago]
    
    colors = {"daypack": "#2563eb", "allday": "#ea580c", "daynhalf": "#10b981"}
    
    exact_stats = {name: [] for name in colors.keys()}
    daily_stats = {name: {} for name in colors.keys()}
    
    for item in history:
        name = item.get('item', 'daypack')
        if name not in colors:
            continue
        dt_str = item['timestamp']
        date_str = dt_str[:10]
        price = item['price'] / 1000.0
        
        # 모든 관측 데이터 수집
        dt_obj = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
        exact_stats[name].append((dt_obj, price))
        
        # 범위 밴드를 위한 일일 최저/최고가 수집
        if date_str not in daily_stats[name]:
            daily_stats[name][date_str] = {'min': price, 'max': price}
        else:
            daily_stats[name][date_str]['min'] = min(daily_stats[name][date_str]['min'], price)
            daily_stats[name][date_str]['max'] = max(daily_stats[name][date_str]['max'], price)

    all_prices = []
    
    for item_name, line_color in colors.items():
        if not exact_stats[item_name]:
            continue
            
        exact_stats[item_name].sort(key=lambda x: x[0])
        e_dates = [x[0] for x in exact_stats[item_name]]
        e_prices = [x[1] for x in exact_stats[item_name]]
        all_prices.extend(e_prices)
        
        # 1. 최저-최고 범위 직선 대역
        if daily_stats[item_name]:
            sorted_dates = sorted(daily_stats[item_name].keys())
            mins = [daily_stats[item_name][d]['min'] for d in sorted_dates]
            maxs = [daily_stats[item_name][d]['max'] for d in sorted_dates]
            d_dates = [datetime.strptime(d, '%Y-%m-%d') for d in sorted_dates]
            
            plt.fill_between(d_dates, mins, maxs, color=line_color, alpha=0.06, edgecolor='none')
            
        # 범례(Legend)에 점과 선이 모두 나오도록 가짜(Dummy) 선 그리기
        plt.plot([], [], marker='o', color=line_color, linewidth=1.0, 
                 markersize=4.5, markerfacecolor='#ffffff', markeredgewidth=1.0, label=item_name.upper())
                 
        # 2. 모든 관측 가격 메인 실선 (마커 없음)
        plt.plot(e_dates, e_prices, color=line_color, linewidth=1.0)
        
        bbox_props = dict(boxstyle="round,pad=0.2", fc="#ffffff", ec=line_color, lw=1.0, alpha=0.8)
        
        # 날짜별로 인덱스를 묶고, 그날의 최저가 중 '마지막' 관측치만 선별
        day_to_indices = {}
        for i, dt in enumerate(e_dates):
            d_str = dt.strftime('%Y-%m-%d')
            if d_str not in day_to_indices:
                day_to_indices[d_str] = []
            day_to_indices[d_str].append(i)
            
        daily_last_min_indices = []
        for d_str in sorted(day_to_indices.keys()):
            indices = day_to_indices[d_str]
            min_p = min(e_prices[i] for i in indices)
            last_min_idx = [i for i in indices if e_prices[i] == min_p][-1]
            daily_last_min_indices.append(last_min_idx)
            
        # 동일 가격 연속 시 가로 겹침 방지 필터링
        annot_indices = []
        for i, idx in enumerate(daily_last_min_indices):
            if i == len(daily_last_min_indices) - 1:
                annot_indices.append(idx)
            else:
                next_idx = daily_last_min_indices[i+1]
                if e_prices[idx] != e_prices[next_idx]:
                    annot_indices.append(idx)
        
        # 3. 스마트하게 선별된 포인트에만 '점(Dot)', '라벨', '시간' 부착
        for i in annot_indices:
            txt = e_prices[i]
            dt_obj = e_dates[i]
            time_str = dt_obj.strftime('%H:%M')
            
            # 점(Marker)
            plt.plot(dt_obj, txt, marker='o', color=line_color, linewidth=0, 
                     markersize=4.5, markerfacecolor='#ffffff', markeredgewidth=1.0)
            
            # 다른 아이템과 세로로 겹치지 않도록 방지하는 순위 계산 (가격이 15k 차이 이내일 때만 피함)
            higher_count = 0
            for nm in colors.keys():
                if nm != item_name and exact_stats[nm]:
                    nm_prices_before = [p for d, p in exact_stats[nm] if d <= dt_obj]
                    if nm_prices_before:
                        other_price = nm_prices_before[-1]
                        if abs(other_price - txt) < 15:
                            if other_price > txt:
                                higher_count += 1
                            elif other_price == txt and nm > item_name:
                                higher_count += 1
                            
            # 위치에 따라 가격 말풍선과 시간 텍스트 좌표 상/중/하 분리
            if higher_count == 0:
                xy_offset_price = (0, 16)
                xy_offset_time = (0, 6)
            elif higher_count == 1:
                xy_offset_price = (0, -14)
                xy_offset_time = (0, -23)
            else:
                xy_offset_price = (0, -36)
                xy_offset_time = (0, -45)

            # 가격 말풍선
            ann = plt.annotate(f"{txt:,.0f}k", (dt_obj, txt), 
                         textcoords="offset points", xytext=xy_offset_price, 
                         ha='center', fontsize=8, fontweight='700', color=line_color, alpha=0.9,
                         bbox=bbox_props)
            ann.get_bbox_patch().set_path_effects([
                pe.SimplePatchShadow(offset=(1.0, -1.0), shadow_rgbFace='#0f172a', alpha=0.05),
                pe.Normal()
            ])
            
            # 시간 텍스트 (회색, 작은 폰트, 외곽선 효과)
            time_ann = plt.annotate(time_str, (dt_obj, txt), 
                         textcoords="offset points", xytext=xy_offset_time, 
                         ha='center', fontsize=6.5, fontweight='600', color='#64748b', alpha=0.9)
            time_ann.set_path_effects([
                pe.withStroke(linewidth=1.5, foreground='#ffffff', alpha=0.85)
            ])
    
    y_max = max(all_prices) if all_prices else 150
    top_limit = max(y_max * 1.05, 155)
    
    # 하단 범위 조정 (120을 120,000원으로 간주)
    bottom_limit = min(120, all_time_min - 2)
    plt.ylim(bottom_limit, top_limit)
    
    # 역대 최저가 연한 회색 점선
    plt.axhline(y=all_time_min, color='#94a3b8', linestyle=':', linewidth=1.5, alpha=0.8)
    ax.text(0.02, all_time_min + 0.8, f'All-Time Low ({all_time_min:,.0f}k) on {all_time_min_date}', 
            color='#94a3b8', fontweight='bold', fontsize=9, 
            va='bottom', ha='left', transform=ax.get_yaxis_transform())
    
    # 목표가 진한 회색 실선 (150 = 150,000원)
    target_price = 150
    plt.axhline(y=target_price, color='#475569', linestyle='-', linewidth=1.5, alpha=0.8)
    ax.text(0.02, target_price + 1.0, 'Target (150k)', 
            color='#475569', fontweight='bold', fontsize=10, 
            va='bottom', ha='left', transform=ax.get_yaxis_transform())
    
    plt.title('All Observations & Daily Lowest Points (Recent 21 Days)', fontsize=15, fontweight='bold', pad=20, color='#1e293b')
    plt.ylabel('Price (x1,000 KRW)', fontsize=10, fontweight='500', color='#64748b')
    
    # Y축 점선 그리드와 X축 정각(00:00) 기준 얇은 흰색 세로선
    ax.grid(axis='y', linestyle='--', color='#f1f5f9', linewidth=1.5)
    ax.grid(axis='x', linestyle='-', color='#ffffff', linewidth=1.0)
    
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    
    # X축 눈금 간격 1일 고정 (홀수/짝수 모두 표시)
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    plt.gcf().autofmt_xdate(rotation=45) 
    
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
            
            target_days_ago = now_kst - timedelta(days=21)
            recent_item_history = [x for x in item_history if datetime.strptime(x['timestamp'], '%Y-%m-%d %H:%M:%S') > target_days_ago]
            
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
            
            updated_recent = [x for x in history if x.get('item', 'daypack') == item_name and datetime.strptime(x['timestamp'], '%Y-%m-%d %H:%M:%S') > target_days_ago]
            lowest_item = min(updated_recent, key=lambda x: x['price'])
            
            current_results[item_name] = {
                'curr_price': clean_price,
                'low_price': lowest_item['price'],
                'buy_url': buy_url
            }
            
        with open(history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
            
        graph_file = draw_graph(history)

        if new_records_triggered:
            items_str = ", ".join(new_records_triggered)
            header = f"💥💣 <b>[3주 최저가 갱신 ({items_str})!!]</b> 💣💥\n"
        else:
            header = ""

        def format_message(title):
            time_str = now_kst.strftime('%y%m%d %H:%M')
            msg = f"{header}<b>{title}</b>\n\n"
            msg += f"알림시각 : {time_str}\n"
            msg += "상품가격(현재가/3주 최저가)\n"
            for name in ["daypack", "allday", "daynhalf"]:
                if name in current_results:
                    res = current_results[name]
                    msg += f"-{name.upper()} : {res['curr_price']:,} / {res['low_price']:,}\n"
            return msg.strip()
            
        cron_trigger = os.environ.get('CRON_TRIGGER', '')
        is_regular_report = (cron_trigger == '0 0,12 * * *') or (cron_trigger == '')
        
        inline_keyboard = []
        for name in ["daypack", "allday", "daynhalf"]:
            if name in current_results:
                inline_keyboard.append([{"text": f"🛒 {name.upper()} 최저가 바로가기", "url": current_results[name]['buy_url']}])
                
        reply_markup = {"inline_keyboard": inline_keyboard}
        
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
