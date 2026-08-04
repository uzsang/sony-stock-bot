import os
import re
import json
import requests
import numpy as np
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
from sklearn.linear_model import LinearRegression

# ==========================================
# 1. 설정 및 상수 (Configuration)
# ==========================================
ITEMS_INFO = {
    "daypack": "https://search.danawa.com/dsearch.php?query=09J29360&originalQuery=09J29360&checkedInfo=N&volumeType=allvs&page=1&limit=40&sort=priceASC&list=list&boost=true&tab=main&addDelivery=N",
    "allday": "https://search.danawa.com/dsearch.php?query=09J09243&originalQuery=09J09243&checkedInfo=N&volumeType=allvs&page=1&limit=40&sort=priceASC&list=list&boost=true&tab=main&addDelivery=N",
    "daynhalf": "https://search.danawa.com/dsearch.php?query=09J29453&originalQuery=09J29453&checkedInfo=N&volumeType=allvs&page=1&limit=40&sort=priceASC&list=list&boost=true&tab=main&addDelivery=N"
}

ITEM_COLORS = {"daypack": "#2563eb", "allday": "#ea580c", "daynhalf": "#10b981"}
HISTORY_FILE = 'price_history.json'
GRAPH_FILE = 'price_graph.png'
TARGET_PRICE = 150

# ==========================================
# 2. 데이터 처리 및 유틸리티 (Data & Utils)
# ==========================================
def load_history(filepath):
    """JSON 파일에서 과거 데이터를 불러옵니다."""
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_history(filepath, history_data):
    """업데이트된 데이터를 JSON 파일에 저장합니다."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(history_data, f, ensure_ascii=False, indent=2)

def extract_buy_url(price_element, default_url):
    """가격 요소에서 가장 안전한 구매 링크를 추출합니다."""
    try:
        li_parent = price_element.find_element(By.XPATH, "./ancestor::li[1]")
        link_el = li_parent.find_element(By.CSS_SELECTOR, ".prod_pricelist li:first-child a")
        url = link_el.get_attribute("href")
        if url and "javascript" not in url:
            return url
    except Exception:
        pass
    
    try:
        return price_element.find_element(By.XPATH, "./ancestor::a").get_attribute("href")
    except Exception:
        return default_url

# ==========================================
# 3. 그래프 생성 (Matplotlib & ML)
# ==========================================
def draw_graph(full_history):
    if not full_history:
        return None
        
    # 기본 폰트 및 테마 설정
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Helvetica Neue', 'Helvetica', 'Arial', 'sans-serif']
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_facecolor('#f8f9fa')
    fig.patch.set_facecolor('#ffffff')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#e2e8f0')
    ax.spines['bottom'].set_color('#e2e8f0')
    
    # 1) 데이터 파싱 및 21일치 필터링
    parsed_history = []
    for item in full_history:
        item_copy = item.copy()
        item_copy['dt_obj'] = datetime.strptime(item['timestamp'], '%Y-%m-%d %H:%M:%S')
        parsed_history.append(item_copy)
        
    # 역대 최저가 추출
    all_time_min_item = min(parsed_history, key=lambda x: x['price'])
    all_time_min = all_time_min_item['price'] / 1000.0
    all_time_min_date = all_time_min_item['timestamp'][:10]
    
    now_kst = datetime.utcnow() + timedelta(hours=9)
    target_days_ago = now_kst - timedelta(days=21)
    
    recent_history = [item for item in parsed_history if item['dt_obj'] > target_days_ago]
    
    # 2) 아이템별 데이터 그룹화
    exact_stats = {name: [] for name in ITEM_COLORS.keys()}
    daily_stats = {name: {} for name in ITEM_COLORS.keys()}
    
    for item in recent_history:
        name = item.get('item', 'daypack')
        if name not in ITEM_COLORS: continue
        
        price = item['price'] / 1000.0
        dt_obj = item['dt_obj']
        date_str = dt_obj.strftime('%Y-%m-%d')
        
        exact_stats[name].append((dt_obj, price))
        
        if date_str not in daily_stats[name]:
            daily_stats[name][date_str] = {'min': price, 'max': price}
        else:
            daily_stats[name][date_str]['min'] = min(daily_stats[name][date_str]['min'], price)
            daily_stats[name][date_str]['max'] = max(daily_stats[name][date_str]['max'], price)

    all_prices = []
    bbox_props = dict(boxstyle="round,pad=0.2", fc="#ffffff", ec="none", lw=0, alpha=0.85)
    
    # 3) 아이템별 그래프 그리기
    for item_name, line_color in ITEM_COLORS.items():
        if not exact_stats[item_name]: continue
            
        exact_stats[item_name].sort(key=lambda x: x[0])
        e_dates = [x[0] for x in exact_stats[item_name]]
        e_prices = [x[1] for x in exact_stats[item_name]]
        all_prices.extend(e_prices)
        
        # 음영 범위(밴드)
        if daily_stats[item_name]:
            sorted_dates = sorted(daily_stats[item_name].keys())
            mins = [daily_stats[item_name][d]['min'] for d in sorted_dates]
            maxs = [daily_stats[item_name][d]['max'] for d in sorted_dates]
            d_dates = [datetime.strptime(d, '%Y-%m-%d') for d in sorted_dates]
            ax.fill_between(d_dates, mins, maxs, color=line_color, alpha=0.06, edgecolor='none')
            
        # 더미 선 (범례용) 및 메인 실선
        ax.plot([], [], marker='o', color=line_color, linewidth=1.5, markersize=4.5, 
                markerfacecolor='#ffffff', markeredgewidth=1.5, label=item_name.upper())
        ax.plot(e_dates, e_prices, color=line_color, linewidth=1.5)

        # 머신러닝 예측선 (꼬리 부분)
        if len(e_dates) >= 3:
            X_time = mdates.date2num(e_dates).reshape(-1, 1)
            X_weekday = np.array([dt.weekday() for dt in e_dates]).reshape(-1, 1)
            X_train = np.hstack((X_time, X_weekday)) 
            y_train = np.array(e_prices)
            
            model = LinearRegression()
            model.fit(X_train, y_train)
            
            accuracy_pct = max(0.0, model.score(X_train, y_train) * 100)
            
            future_dates = [e_dates[-1] + timedelta(days=i) for i in range(1, 4)]
            X_pred_time = mdates.date2num(future_dates).reshape(-1, 1)
            X_pred_weekday = np.array([dt.weekday() for dt in future_dates]).reshape(-1, 1)
            
            y_pred = model.predict(np.hstack((X_pred_time, X_pred_weekday)))
            
            plot_dates = [e_dates[-1]] + future_dates
            plot_prices = [e_prices[-1]] + list(y_pred)
            
            ax.plot(plot_dates, plot_prices, color=line_color, linestyle=':', linewidth=1.5, alpha=0.7)
            ax.text(plot_dates[-1], plot_prices[-1], f' Pred ({accuracy_pct:.1f}%)', 
                     color=line_color, fontsize=6, fontweight='bold', alpha=0.9)

        # 상승 직전 저점 필터링 로직
        candidate_indices = [i for i in range(len(e_prices) - 1) if e_prices[i] < e_prices[i+1]]
        if e_prices: candidate_indices.append(len(e_prices) - 1)
            
        day_to_candidates = {}
        for idx in candidate_indices:
            day_to_candidates.setdefault(e_dates[idx].strftime('%Y-%m-%d'), []).append(idx)
            
        annot_indices = []
        for indices in day_to_candidates.values():
            min_p = min(e_prices[i] for i in indices)
            best_idx = [i for i in indices if e_prices[i] == min_p][-1]
            annot_indices.append(best_idx)
            
        # 어노테이션(말풍선) 부착
        for idx in sorted(annot_indices):
            txt = e_prices[idx]
            dt_obj = e_dates[idx]
            
            ax.plot(dt_obj, txt, marker='o', color=line_color, linewidth=0, 
                     markersize=5.0, markerfacecolor='#ffffff', markeredgewidth=1.5)
            
            # 겹침 방지 (Higher count)
            higher_count = sum(
                1 for nm, data in exact_stats.items()
                if nm != item_name and data
                for d, p in [data[-1] if data else (None, None)]
                if [val for d_val, val in data if d_val <= dt_obj] 
                and abs([val for d_val, val in data if d_val <= dt_obj][-1] - txt) < 15
                and ([val for d_val, val in data if d_val <= dt_obj][-1] > txt or 
                    ([val for d_val, val in data if d_val <= dt_obj][-1] == txt and nm > item_name))
            )
            
            # 💡 가격 말풍선과 시간 간격을 넓히고 정렬을 맞춤 (Y축 간격 16px 통일)
            xy_offsets = [(0, 24), (0, -16), (0, -48)]
            time_offsets = [(0, 8), (0, -32), (0, -64)]
            offset_idx = min(higher_count, 2)

            ann = ax.annotate(f"{txt:,.0f}k", (dt_obj, txt), 
                         textcoords="offset points", xytext=xy_offsets[offset_idx], 
                         ha='center', fontsize=8, fontweight='700', color=line_color, alpha=0.9,
                         bbox=bbox_props, rotation=45)
            ann.get_bbox_patch().set_path_effects([
                pe.SimplePatchShadow(offset=(1.0, -1.0), shadow_rgbFace='#0f172a', alpha=0.08), pe.Normal()
            ])
            
            time_ann = ax.annotate(dt_obj.strftime('%H:%M'), (dt_obj, txt), 
                         textcoords="offset points", xytext=time_offsets[offset_idx], 
                         ha='center', fontsize=6.5, fontweight='700', color='#64748b', alpha=1.0, rotation=45)
            time_ann.set_path_effects([pe.withStroke(linewidth=1.5, foreground='#ffffff', alpha=0.9)])
    
    # 4) 그래프 축 및 레이아웃 정리
    y_max = max(all_prices) if all_prices else TARGET_PRICE
    ax.set_ylim(min(120, all_time_min - 2), max(y_max * 1.05, 155))
    
    # 기준선 (역대 최저가 및 목표가)
    ax.axhline(y=all_time_min, color='#94a3b8', linestyle=':', linewidth=1.5, alpha=0.8)
    ax.text(0.02, all_time_min - 0.5, f'All-Time Low ({all_time_min:,.0f}k) on {all_time_min_date}', 
            color='#94a3b8', fontweight='bold', fontsize=9, va='top', ha='left', transform=ax.get_yaxis_transform())
    
    ax.axhline(y=TARGET_PRICE, color='#475569', linestyle='-', linewidth=1.5, alpha=0.8)
    ax.text(0.02, TARGET_PRICE + 1.0, f'Target ({TARGET_PRICE}k)', 
            color='#475569', fontweight='bold', fontsize=10, va='bottom', ha='left', transform=ax.get_yaxis_transform())
    
    ax.set_title('ML Predicted Trend & Daily Pre-Rise Lowest Points', fontsize=15, fontweight='bold', pad=20, color='#1e293b')
    ax.set_ylabel('Price (x1,000 KRW)', fontsize=10, fontweight='500', color='#64748b')
    
    ax.grid(axis='y', linestyle='--', color='#f1f5f9', linewidth=1.5)
    ax.grid(axis='x', linestyle='-', color='#ffffff', linewidth=1.0)
    
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    fig.autofmt_xdate(rotation=45) 
    
    ax.tick_params(colors='#64748b', labelsize=9)
    ax.legend(loc='lower right', frameon=True, facecolor='#ffffff', edgecolor='#e2e8f0', 
               fontsize=9, labelcolor='#334155', borderpad=0.8)
    
    plt.savefig(GRAPH_FILE, bbox_inches='tight', dpi=150) 
    plt.close(fig) # 메모리 누수 방지
    
    return GRAPH_FILE

# ==========================================
# 4. 가격 수집 (Selenium)
# ==========================================
def fetch_current_prices(driver):
    current_results = {}
    now_kst = datetime.utcnow() + timedelta(hours=9)
    now_str = now_kst.strftime('%Y-%m-%d %H:%M:%S')
    wait = WebDriverWait(driver, 10)
    
    for item_name, url in ITEMS_INFO.items():
        try:
            driver.get(url)
            price_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "p.price_sect strong")))
            clean_price = int(re.sub(r'[^0-9]', '', price_element.text))
            buy_url = extract_buy_url(price_element, url)
            
            current_results[item_name] = {
                'timestamp': now_str,
                'price': clean_price,
                'text': price_element.text,
                'buy_url': buy_url
            }
        except Exception as e:
            print(f"Error fetching {item_name}: {e}")
            
    return current_results, now_kst

# ==========================================
# 5. 메인 로직 및 텔레그램 연동
# ==========================================
def build_messages(current_results, history, new_records_triggered, now_kst, graph_file):
    if new_records_triggered:
        header = f"💥💣 <b>[3주 최저가 갱신 ({', '.join(new_records_triggered)})!!]</b> 💣💥\n"
    else:
        header = ""

    def format_message(title):
        msg = f"{header}<b>{title}</b>\n\n알림시각 : {now_kst.strftime('%y%m%d %H:%M')}\n상품가격(현재가/3주 최저가)\n"
        for name in ITEM_COLORS.keys():
            if name in current_results:
                curr_p = current_results[name]['price']
                # 3주 이내 최저가 계산
                target_days_ago = now_kst - timedelta(days=21)
                recent = [x['price'] for x in history if x.get('item') == name and datetime.strptime(x['timestamp'], '%Y-%m-%d %H:%M:%S') > target_days_ago]
                low_p = min(recent) if recent else curr_p
                msg += f"-{name.upper()} : {curr_p:,} / {low_p:,}\n"
        return msg.strip()

    inline_keyboard = [[{"text": f"🛒 {name.upper()} 최저가 바로가기", "url": res['buy_url']}] 
                       for name, res in current_results.items()]
    reply_markup = {"inline_keyboard": inline_keyboard}
    
    cron_trigger = os.environ.get('CRON_TRIGGER', '')
    is_regular_report = (cron_trigger == '0 23 * * *') or (cron_trigger == '')
    
    messages = []
    if is_regular_report:
        messages.append({"target": "regular", "text": format_message("📊 [정기 브리핑]"), "graph": graph_file, "reply_markup": reply_markup})
    
    messages.append({"target": "watch", "text": format_message("🔔 [수시 브리핑]"), "graph": graph_file, "reply_markup": reply_markup})
    return messages

def send_telegram(results):
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    if not chat_id or not results: return
        
    for item in results:
        token = os.environ.get('TELEGRAM_TOKEN_REGULAR') if item["target"] == "regular" else os.environ.get('TELEGRAM_TOKEN')
        if not token: continue
            
        data = {'chat_id': chat_id, 'caption': item["text"], 'parse_mode': 'HTML'}
        if item.get("reply_markup"):
            data['reply_markup'] = json.dumps(item["reply_markup"])
            
        graph_file = item.get("graph")
        if graph_file and os.path.exists(graph_file):
            with open(graph_file, 'rb') as f:
                requests.post(f"https://api.telegram.org/bot{token}/sendPhoto", data=data, files={'photo': f})
        else:
            data['text'] = data.pop('caption')
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data=data)

def main():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)')

    driver = webdriver.Chrome(options=options)
    history = load_history(HISTORY_FILE)
    
    try:
        current_results, now_kst = fetch_current_prices(driver)
        
        target_days_ago = now_kst - timedelta(days=21)
        new_records_triggered = []
        
        for name, data in current_results.items():
            recent_prices = [x['price'] for x in history if x.get('item') == name and datetime.strptime(x['timestamp'], '%Y-%m-%d %H:%M:%S') > target_days_ago]
            if recent_prices and data['price'] < min(recent_prices):
                new_records_triggered.append(name)
                
            history.append({
                'item': name,
                'timestamp': data['timestamp'],
                'price': data['price'],
                'text': data['text']
            })
            
        save_history(HISTORY_FILE, history)
        graph_file = draw_graph(history)
        
        messages = build_messages(current_results, history, new_records_triggered, now_kst, graph_file)
        send_telegram(messages)
        
    except Exception as e:
        error_msg = [{"target": "watch", "text": f"⚠️ 가격 조회 시스템 에러 발생:\n{str(e)}", "graph": None, "reply_markup": None}]
        send_telegram(error_msg)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
