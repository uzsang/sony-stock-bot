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
    
    plt.figure(figsize=(9, 5))
    ax = plt.gca()
    
    ax.set_facecolor('#f8f9fa')
    plt.gcf().patch.set_facecolor('#ffffff')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#dddddd')
    ax.spines['bottom'].set_color('#dddddd')
    
    line_color = '#4361ee'
    plt.plot(dates, sorted_prices, marker='o', color=line_color, linewidth=2.5, markersize=8, markerfacecolor='#ffffff', markeredgewidth=2)
    
    y_max = max(sorted_prices)
    
    # Y축 최솟값을 10만원으로 고정, 목표가(15만원)가 잘 보이도록 최댓값 설정
    top_limit = max(y_max * 1.05, 155000)
    plt.ylim(100000, top_limit)
    
    # 그래프 아래 반투명 색상 채우기
    plt.fill_between(dates, sorted_prices, 100000, color=line_color, alpha=0.1)
    
    # 💡 [변경] 15만 원 위치에 목표가 빨간색 '실선(linestyle='-')' 추가
    target_price = 150000
    plt.axhline(y=target_price, color='#FF4B4B', linestyle='-', linewidth=2, alpha=0.8)
    plt.text(dates[0], target_price + 1500, 'Target (150,000 won)', color='#FF4B4B', fontweight='bold', fontsize=10)
