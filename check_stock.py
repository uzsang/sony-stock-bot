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
    
    # 다크 모드 색상 팔레트 정의
    bg_color = '#0f172a'
    ax_bg_color = '#0f172a'
    text_main = '#f8fafc'
    text_sub = '#94a3b8'
    grid_color = '#1e293b'
    spine_color = '#334155'
    
    ax.set_facecolor(ax_bg_color)
    plt.gcf().patch.set_facecolor(bg_color)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(spine_color)
    ax.spines['bottom'].set_color(spine_color)
    
    # 역대 최저가 및 날짜 추출
    all_time_min_item = min(full_history, key=lambda x: x['price'])
    all_time_min = all_time_min_item['price'] / 1000.0
    all_time_min_date = all_time_min_item['timestamp'][:10]
    
    now_kst = datetime.utcnow() + timedelta(hours=9)
    target_days_ago = now_kst - timedelta(days=21)
    history = [item for item in full_history if datetime.strptime(item['timestamp'], '%Y-%m-%d %H:%M:%S') > target_days_ago]
    
    colors = {"daypack": "#60a5fa", "allday": "#fb923c", "daynhalf": "#34d399"}
    
    exact_stats = {name: [] for name in colors.keys()}
    daily_stats = {name: {} for name in colors.keys()}
    
    for item in history:
        name = item.get('item', 'daypack')
        if name not in colors:
            continue
        dt_str = item['timestamp']
        date_str = dt_str[:10]
        price = item['price'] / 1000.0
        
        dt_obj = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
        exact_stats[name].append((dt_obj, price))
        
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
        
        # 최저-최고 범위 대역
        if daily_stats[item_name]:
            sorted_dates = sorted(daily_stats[item_name].keys())
            mins = [daily_stats[item_name][d]['min'] for d in sorted_dates]
            maxs = [daily_stats[item_name][d]['max'] for d in sorted_dates]
            d_dates = [datetime.strptime(d, '%Y-%m-%d') for d in sorted_dates]
            
            plt.fill_between(d_dates, mins, maxs, color=line_color, alpha=0.1, edgecolor='none')
            
        # 가짜(Dummy) 선 그리기 (범례용)
        plt.plot([], [], marker='o', color=line_color, linewidth=1.5, 
                 markersize=4.5, markerfacecolor=bg_color, markeredgewidth=1.5, label=item_name.upper())
        
        # 메인 실선 그리기
        plt.plot(e_dates, e_prices, color=line_color, linewidth=1.5)

        # 🤖 [핵심 변경] 머신러닝 예측선 (시간 + 요일 학습)
        if len(e_dates) >= 3:
            # 1. Feature(시간 숫자값, 요일 0~6) 와 Target(가격) 분리
            X_time = mdates.date2num(e_dates).reshape(-1, 1)
            X_weekday = np.array([dt.weekday() for dt in e_dates]).reshape(-1, 1)
            X_train = np.hstack((X_time, X_weekday)) # 시간과 요일을 합쳐서 2개의 특징(Feature) 사용
            y_train = np.array(e_prices)
            
            # 2. scikit-learn 선형 회귀 모델 학습
            model = LinearRegression()
            model.fit(X_train, y_train)
            
            # 💡 [정확도 계산] R-squared 값을 통해 학습 정확도를 %로 계산
            r2_score = model.score(X_train, y_train)
            accuracy_pct = max(0.0, r2_score * 100) # 신뢰도가 마이너스로 떨어지는 것을 방지
            
            # 3. 마지막 관측일 기준 향후 3일(내일, 모레, 글피) 생성
            future_dates = [e_dates[-1] + timedelta(days=i) for i in range(1, 4)]
            X_pred_time = mdates.date2num(future_dates).reshape(-1, 1)
            X_pred_weekday = np.array([dt.weekday() for dt in future_dates]).reshape(-1, 1)
            X_pred = np.hstack((X_pred_time, X_pred_weekday))
            
            # 가격 예측
            y_pred = model.predict(X_pred)
            
            # 4. 실선과 이어지도록 마지막 관측점을 포함하여 점선 그리기
            plot_dates = [e_dates[-1]] + future_dates
            plot_prices = [e_prices[-1]] + list(y_pred)
            
            plt.plot(plot_dates, plot_prices, color=line_color, linestyle=':', linewidth=1.5, alpha=0.7)
            
            # 💡 [정확도 표시] 예측선 끝부분에 라벨과 정확도 % 부착
            plt.text(plot_dates[-1], plot_prices[-1], f' Pred ({accuracy_pct:.1f}%)', 
                     color=line_color, fontsize=6, fontweight='bold', alpha=0.9)

        # 말풍선 스타일 다크 테마 적용
        bbox_props = dict(boxstyle="round,pad=0.2", fc="#1e293b", ec="none", lw=0, alpha=0.85)
        
        # 1차 필터링: '가격 상승 직전(저점)' 포인트 및 '마지막' 관측치 선별
        candidate_indices = set()
        for i in range(len(e_prices) - 1):
            if e_prices[i] < e_prices[i+1]:
                candidate_indices.add(i)
        if e_prices:
            candidate_indices.add(len(e_prices) - 1)
            
        # 2차 필터링: 같은 날짜에 여러 후보가 있다면 '최저가' 딱 하나만 남김
        day_to_candidates = {}
        for idx in candidate_indices:
            d_str = e_dates[idx].strftime('%Y-%m-%d')
            if d_str not in day_to_candidates:
                day_to_candidates[d_str] = []
            day_to_candidates[d_str].append(idx)
            
        annot_indices = set()
        for d_str, indices in day_to_candidates.items():
            min_p = min(e_prices[i] for i in indices)
            best_idx = [i for i in indices if e_prices[i] == min_p][-1]
            annot_indices.add(best_idx)
            
        # 하락폭 계산 로직
        sorted_annots = sorted(list(annot_indices))
        prev_p = None
        
        for idx in sorted_annots:
            txt = e_prices[idx]
            dt_obj = e_dates[idx]
            time_str = dt_obj.strftime('%H:%M')
            
            # 이전 저점보다 떨어졌다면 하락폭(▼) 문자열 생성
            drop_str = ""
            if prev_p is not None and txt < prev_p:
                drop_val = prev_p - txt
                drop_str = f" ▼{drop_val:,.0f}k"
                
            prev_p = txt
            
            # 다크 모드용 점(Marker)
            plt.plot(dt_obj, txt, marker='o', color=line_color, linewidth=0, 
                     markersize=5.0, markerfacecolor=bg_color, markeredgewidth=1.5)
            
            # 세로 겹침 방지 순위 계산
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
                         bbox=bbox_props, rotation=45)
            # 다크 모드용 그림자
            ann.get_bbox_patch().set_path_effects([
                pe.SimplePatchShadow(offset=(1.0, -1.0), shadow_rgbFace='#000000', alpha=0.4),
                pe.Normal()
            ])
            
            # 시간 + 하락폭 텍스트 합체
            time_display = f"{time_str}{drop_str}"
            time_color = '#38bdf8' if drop_str else text_sub 
            
            time_ann = plt.annotate(time_display, (dt_obj, txt), 
                         textcoords="offset points", xytext=xy_offset_time, 
                         ha='center', fontsize=6.5, fontweight='700', color=time_color, alpha=1.0, rotation=45)
            
            # 다크 모드 배경색(bg_color)으로 테두리를 둘러서 글씨 보호
            time_ann.set_path_effects([
                pe.withStroke(linewidth=1.5, foreground=bg_color, alpha=0.9)
            ])
    
    y_max = max(all_prices) if all_prices else 150
    top_limit = max(y_max * 1.05, 155)
    bottom_limit = min(120, all_time_min - 2)
    plt.ylim(bottom_limit, top_limit)
    
    # 역대 최저가 / 목표가 라인 색상 조정
    plt.axhline(y=all_time_min, color='#475569', linestyle=':', linewidth=1.5, alpha=0.8)
    ax.text(0.02, all_time_min + 0.8, f'All-Time Low ({all_time_min:,.0f}k) on {all_time_min_date}', 
            color='#64748b', fontweight='bold', fontsize=9, 
            va='bottom', ha='left', transform=ax.get_yaxis_transform())
    
    target_price = 150
    plt.axhline(y=target_price, color='#64748b', linestyle='-', linewidth=1.5, alpha=0.8)
    ax.text(0.02, target_price + 1.0, 'Target (150k)', 
            color='#94a3b8', fontweight='bold', fontsize=10, 
            va='bottom', ha='left', transform=ax.get_yaxis_transform())
    
    plt.title('ML Predicted Trend & Daily Pre-Rise Lowest Points', fontsize=15, fontweight='bold', pad=20, color=text_main)
    plt.ylabel('Price (x1,000 KRW)', fontsize=10, fontweight='500', color=text_sub)
    
    # 다크 모드용 어두운 그리드 라인
    ax.grid(axis='y', linestyle='--', color=grid_color, linewidth=1.0)
    ax.grid(axis='x', linestyle='-', color=grid_color, linewidth=1.0)
    
    ax.yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.0f}'))
    
    ax.xaxis.set_major_locator(mdates.DayLocator(interval=1))
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    plt.gcf().autofmt_xdate(rotation=45) 
    
    ax.tick_params(colors=text_sub, labelsize=9)
    
    # 다크 모드용 범례 테마
    plt.legend(loc='lower right', frameon=True, facecolor='#1e293b', edgecolor=spine_color, 
               fontsize=9, labelcolor=text_main, borderpad=0.8)
    
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
