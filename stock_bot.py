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
    'TIGER US Dividend Dow Jones': '458730.KS'
}

# 모던 디자인 색상 팔레트
MAIN_COLOR = '#1A73E8'     # 현재가 (파랑)
MA_COLOR = '#FF9500'       # 이동평균선 (주황)
RETURN_COLOR = '#34A853'   # 수익률 보조선 (초록)
TEXT_COLOR = '#202124'  
SUB_TEXT_COLOR = '#5F6368' 
BG_COLOR = '#FFFFFF'    
GRID_COLOR = '#F1F3F4'  

# 아이폰 화면비율에 맞춘 세로형 피겨 생성
fig, axes = plt.subplots(3, 1, figsize=(9, 15.5), facecolor=BG_COLOR)
today_str = datetime.now().strftime("%Y-%m-%d")

# 전체 제목과 부제목 간격 분리 (겹침 방지)
fig.suptitle('Market Overview', fontsize=22, fontweight='medium', color=TEXT_COLOR, y=0.97)
fig.text(0.5, 0.945, f'Korean Listed US ETFs 3-Year Trend ({today_str})', 
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
    # 수익률 line: 훨씬 얇게(0.5), 투명도 80%(alpha=0.8)
    line3 = ax2.plot(close_prices.index, return_rates, color=RETURN_COLOR, linewidth=0.5, linestyle='--', alpha=0.8, label='Return Rate (%)')
    
    # 보조축 글자 색상을 메인축과 동일한 색상으로 통일
    ax2.tick_params(axis='y', colors=SUB_TEXT_COLOR, labelsize=10, length=0, pad=10)
    for spine in ax2.spines.values():
        spine.set_visible(False)
    
    # 개별 차트 제목 설정
    ax.set_title(name, fontsize=13, fontweight='normal', color=TEXT_COLOR, pad=12, loc='center')
    
    # 범례를 그래프별 제목 옆(오른쪽 상단 바깥쪽)으로 배치하여 내용과 겹치지 않게 분리
    lines = line1 + line2 + line3
    labels = [l.get_label() for l in lines]
    ax.legend(lines, labels, loc='upper right', bbox_to_anchor=(1.0, 1.15), frameon=False, fontsize=8, labelcolor=SUB_TEXT_COLOR, ncol=3)
    
    # 주축 불필요한 테두리 제거
    for spine in ax.spines.values():
        spine.set_visible(False)
        
    # 가로 눈금선
    ax.grid(axis='y', color=GRID_COLOR, linestyle='-', linewidth=1.5)
    ax.grid(axis='x', visible=False)
    
    # 주축 라벨 디자인
    ax.tick_params(axis='both', which='major', labelsize=10, colors=SUB_TEXT_COLOR, length=0, pad=10)
    
    # X축 날짜 포맷 ('연도-월')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))

# 여백 및 그래프 간 간격 조정
plt.tight_layout(rect=[0, 0.02, 1, 0.92], h_pad=5.5)
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
