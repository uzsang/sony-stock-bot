import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import requests
import os
from datetime import datetime

# 텔레그램 설정
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# 조회할 티커 심볼
tickers = {
    'TIGER US S&P 500': '360750.KS', 
    'TIGER US NASDAQ 100': '133690.KS', 
    'TIGER US Dividend\nDow Jones': '458730.KS'
}

# 모던 디자인 색상 팔레트
MAIN_COLOR = '#1A73E8'     # 현재가 (파랑)
MA_COLOR = '#FF9500'       # 이동평균선 (주황)
RETURN_COLOR = '#34A853'   # 수익률 보조선 (초록)
TEXT_COLOR = '#202124'  
SUB_TEXT_COLOR = '#5F6368' 
BG_COLOR = '#FFFFFF'    
GRID_COLOR = '#F1F3F4'  
VERTICAL_GRID_COLOR = '#E8EAED' 

# 아이폰 화면비율에 맞춘 세로형 피겨 생성
fig, axes = plt.subplots(3, 1, figsize=(9, 14.5), facecolor=BG_COLOR)
today_str = datetime.now().strftime("%Y-%m-%d")

# 1. 전체 제목과 부제목 위치를 최상단으로 올려 첫 그래프와의 간격을 대폭 축소
fig.suptitle('Market Overview', fontsize=22, fontweight='medium', color=TEXT_COLOR, y=0.99)
fig.text(0.5, 0.965, f'Korean Listed US ETFs 3-Year Trend ({today_str})', 
         ha='center', fontsize=12, color=SUB_TEXT_COLOR)

for ax, (name, ticker) in zip(axes, tickers.items()):
    ax.set_facecolor(BG_COLOR)
    
    # 3년치 데이터 다운로드
    data = yf.download(ticker, period='3y')
    close_prices = data['Close'].squeeze()
    
    # 60일 이평선 계산
    ma_60 = close_prices.rolling(window=60).mean()
    
    # 해당일 구매 시 현재 수익률 계산 (%)
    current_price = close_prices.iloc[-1]
    return_rates = (current_price - close_prices) / close_prices * 100
    
    # Y축 최소값/최대값 타이트하게 계산
    min_price = close_prices.min()
    max_price = close_prices.max()
    padding = (max_price - min_price) * 0.1
    bottom_limit = min_price - padding
    ax.set_ylim(bottom_limit, max_price + padding)
    
    # 메인 주가 선
    line1 = ax.plot(close_prices.index, close_prices, color=MAIN_COLOR, linewidth=1.2, alpha=0.8, label='Price')
    ax.fill_between(close_prices.index, close_prices, bottom_limit, color=MAIN_COLOR, alpha=0.05)
    
    # 60일 이동평균선
    line2 = ax.plot(close_prices.index, ma_60, color=MA_COLOR, linewidth=1.0, alpha=0.8, label='60-Day MA')
    
    # === 보조축(수익률) 추가 ===
    ax2 = ax.twinx()
    line3 = ax2.plot(close_prices.index, return_rates, color=RETURN_COLOR, linewidth=0.5, linestyle='--', alpha=0.8, label='Return Rate (%)')
    
    # 보조축 글자 색상 통일
    ax2.tick_params(axis='y', colors=SUB_TEXT_COLOR, labelsize=10, length=0, pad=10)
    for spine in ax2.spines.values():
        spine.set_visible(False)
    
    # 개별 차트 제목 설정
    ax.set_title(name, fontsize=12, fontweight='normal', color=TEXT_COLOR, pad=10, loc='center', linespacing=1.3)
    
    # 2. 범례를 그래프 내부(좌측 상단)에 한 줄(ncol=3)로 배치
    lines = line1 + line2 + line3
    labels = [l.get_label() for l in lines]
    ax.legend(lines, labels, loc='upper left', frameon=True, facecolor=BG_COLOR, edgecolor='none', fontsize=8, labelcolor=SUB_TEXT_COLOR, ncol=3)
    
    # 주축 불필요한 테두리 제거
    for spine in ax.spines.values():
        spine.set_visible(False)
        
    # 가로 및 세로 그리드 추가
    ax.grid(axis='y', color=GRID_COLOR, linestyle='-', linewidth=1.5)
    ax.grid(axis='x', color=VERTICAL_GRID_COLOR, linestyle='--', linewidth=0.8, alpha=0.7)
    
    # 주축 라벨 디자인
    ax.tick_params(axis='both', which='major', labelsize=10, colors=SUB_TEXT_COLOR, length=0, pad=10)
    
    # X축 날짜 3개월 간격 설정
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    
    # 3. X축 날짜 값을 45도로 회전하고 우측 정렬
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right')

# 전체 여백 조정 (상단 rect를 0.95로 높여 타이틀과 그래프 간격을 좁힘)
plt.tight_layout(rect=[0, 0.02, 1, 0.95], h_pad=3.5)
image_path = 'tiger_etf_modern.png'
plt.savefig(image_path, dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor())

# 텔레그램 전송
url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
with open(image_path, 'rb') as photo:
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'caption': f'📊 오늘의 주식 시장 요약입니다. ({today_str})\n파란선: 현재가 / 주황선: 60일 이평선 / 초록점선: 해당 일 매수 시 현재 수익률(%)'
    }
    requests.post(url, data=payload, files={'photo': photo})
