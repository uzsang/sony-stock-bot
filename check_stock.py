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

# 💡 [그래프 고도화] 일별 최저가 추출 및 모던한 디자인 적용
def draw_graph(history):
    if not history:
        return None
        
    # 1. 일별 최저가 데이터 정제
    daily_min = {}
    for item in history:
        date_str = item['timestamp'][:10] # 'YYYY-MM-DD' 형식으로 자르기
        price = item['price']
        if date_str not in daily_min or price < daily_min[date_str]:
            daily_min[date_str] = price
            
    # 날짜순으로 정렬
    sorted_dates = sorted(daily_min.keys())
    sorted_prices = [daily_min[d] for d in sorted_dates]
    dates = [datetime.strptime(d, '%Y-%m-%d') for d in sorted_dates]
    
    # 2. 예쁘고 세련된 그래프 그리기
    plt.figure(figsize=(9, 5))
    ax = plt.gca()
    
    # 배경 및 테두리 정리
    ax.set_facecolor('#f8f9fa')
    plt.gcf().patch.set_facecolor('#ffffff')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#dddddd')
    ax.spines['bottom'].set_color('#dddddd')
    
    # 세련된 블루 톤의 선과 마커
    line_color = '#4361ee'
    plt.plot(dates, sorted_prices, marker='o', color=line_color, linewidth=2.5, markersize=8, markerfacecolor='#ffffff', markeredgewidth=2)
    
    # 선 아래쪽 반투명 영역 칠하기 (모던한 대시보드 느낌)
    y_min = min(sorted_prices)
    y_max = max(sorted_prices)
    # 데이터가 1개뿐이거나 가격 변동이 전혀 없을 때를 대비한 예외 처리
    if y_min == y_max:
        plt.ylim(y_min * 0.9, y_min * 1.1)
        fill_base = y_min * 0.9
    else:
        plt.ylim(y_min - (y_max - y_min) * 0.15, y_max + (y_max - y_min) * 0.25)
        fill_base = y_min - (y_max - y_min) * 0.15
        
    plt.fill_between(dates, sorted_prices, fill_base, color=line_color, alpha=0.1)
    
    # 각 점 위에 실제 가격 숫자(콤마 포함) 표시
    for i, txt in enumerate(sorted_prices):
        plt.annotate(f"{txt:,}", (dates[i], sorted_prices[i]), 
                     textcoords="offset points", xytext=(0, 10), 
                     ha='center', fontsize=10, fontweight='bold', color='#333333')
    
    # 타이틀 및 축 설정
    plt.title('Daily Lowest Price (Recent 14 Days)', fontsize=14, fontweight='bold', pad=20, color='#2b2d42')
    plt.ylabel('Price (KRW)', fontsize=10, color='#6c757d')
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    
    # X축 날짜 포맷 깔끔하게 정리 (월-일 형태)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    plt.xticks(dates, rotation=45, color='#6c757d')
    
    graph_path = 'price_graph.png'
    # dpi=150을 주어 화질을 더 선명하게 저장합니다
    plt.savefig(graph_path, bbox_inches='tight', dpi=150) 
    plt.close()
    
    return graph_path

def get_lowest_price():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit
