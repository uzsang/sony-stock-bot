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
MAIN_COLOR = '#1A73E8'  
MA_COLOR = '#FF9500'    
TEXT_COLOR = '#202124'  
SUB_TEXT_COLOR = '#5F6368' 
BG_COLOR = '#FFFFFF'    
GRID_COLOR = '#F1F3F4'  

fig, axes = plt.subplots(3, 1, figsize=(10, 15), facecolor=BG_COLOR)
today_str = datetime.now().strftime("%Y-%m-%d")

# 전체 제목
fig.suptitle('Market Overview', fontsize=24, fontweight='bold', color=TEXT_COLOR, y=0.96)
fig.text(0.5, 0.93, f'Korean Listed US ETFs 3-Year Trend ({today_str})', 
         ha='center', fontsize=12, color=SUB_TEXT_COLOR)

for ax, (name, ticker) in zip(axes, tickers.items()):
    ax.set_facecolor(BG_COLOR)
    
    # 3년치 데이터 다운로드
    data = yf.download(ticker, period='3y')
    close_prices = data['Close'].squeeze()
    
    # 60일 이평선 계산
    ma_60 = close_prices.rolling(window=60).mean()
    
    # Y축 최소값/최대값 타이트하게 계산
    min_price = close_prices.min()
    max_price = close_prices.max()
    padding = (max_price - min_price) * 0.1
    bottom_limit = min_price - padding
    ax.set_ylim(bottom_limit, max_price + padding)
    
    # 메인 주가 선: 얇게(1.2), 투명하게(0.8)
    ax.plot(close_prices.index, close_prices, color=MAIN_COLOR, linewidth=1.2, alpha=0.8, label='Price')
    ax.fill_between(close_prices.index, close_prices, bottom_limit, color=MAIN_COLOR, alpha=0.05)
    
    # 60일(약 3개월) 이동평균선: 더 얇게(1.0), 투명하게(0.8)
    ax.plot(close_prices.index, ma_60, color=MA_COLOR, linewidth=1.0, alpha=0.8, label='60-Day MA')
    
    # 개별 차트 제목 가운데 정렬
    ax.set_title(name, fontsize=14, fontweight='bold', color=TEXT_COLOR, pad=15, loc='center')
    
    # 불필요한 테두리(Spine) 완벽 제거
    for spine in ax.spines.values():
        spine.set_visible(False)
        
    # 부드러운 가로 눈금선만 추가
    ax.grid(axis='y', color=GRID_COLOR, linestyle='-', linewidth=1.5)
    ax.grid(axis='x', visible=False)
    
    # 축 라벨 디자인 단순화
    ax.tick_params(axis='both', which='major', labelsize=10, colors=SUB_TEXT_COLOR, length=0, pad=10)
    
    # X축 날짜 포맷을 '연도-월' 형태의 숫자로 변경 (예: 2026-01)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    
    # 범례가 그래프를 가리지 않도록 차트 우측 상단 밖으로 배치
    ax.legend(loc='lower right', bbox_to_anchor=(1.0, 1.0), frameon=False, fontsize=10, labelcolor=SUB_TEXT_COLOR, ncol=2)

# 여백 및 그래프 간 간격(h_pad)을 넓게 조정
plt.tight_layout(rect=[0, 0.03, 1, 0.90], h_pad=5.0)
image_path = 'tiger_etf_modern.png'
plt.savefig(image_path, dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor())

# 텔레그램 전송
url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
with open(image_path, 'rb') as photo:
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'caption': f'📊 오늘의 주식 시장 요약입니다. ({today_str})\n파란선: 현재가 / 주황선: 60일(3개월) 이동평균선'
    }
    requests.post(url, data=payload, files={'photo': photo})
