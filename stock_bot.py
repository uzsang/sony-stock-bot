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
RETURN_COLOR = '#34A853'   # 수익률 보조축 (초록)
TEXT_COLOR = '#202124'  
SUB_TEXT_COLOR = '#5F6368' 
BG_COLOR = '#FFFFFF'    
GRID_COLOR = '#F1F3F4'  

# 세로 비율 축소 (노치 간섭 방지 및 쾌적한 화면비를 위해 9:15 비율 적용)
fig, axes = plt.subplots(3, 1, figsize=(9, 15), facecolor=BG_COLOR)
today_str = datetime.now().strftime("%Y-%m-%d")

# 전체 제목 (노치를 피하기 위해 y값을 약간 내림)
fig.suptitle('Market Overview', fontsize=22, fontweight='medium', color=TEXT_COLOR, y=0.94)
fig.text(0.5, 0.92, f'Korean Listed US ETFs 3-Year Trend ({today_str})', 
         ha='center', fontsize=12, color=SUB_TEXT_COLOR)

for ax, (name, ticker) in zip(axes, tickers.items()):
    ax.set_facecolor(BG_COLOR)
    
    # 3년치 데이터 다운로드
    data = yf.download(ticker, period='3y')
    close_prices = data['Close'].squeeze()
    
    # 60일 이평선 계산
    ma_60 = close_prices.rolling(window=60).mean()
    
    # 해당일 구매 시 현재 수익률 계산 (%) = (현재가 - 과거가) / 과거가 * 100
    current_price = close_prices.iloc[-1]
    return_rates = (current_price - close_prices) / close_prices * 100
    
    # Y축 최소값/최대값 타이트하게 계산 (왼쪽 주축)
    min_price = close_prices.min()
    max_price = close_prices.max()
    padding = (max_price - min_price) * 0.1
    bottom_limit = min_price - padding
    ax.set_ylim(bottom_limit, max_price + padding)
    
    # 메인 주가 선: 얇게(1.2), 투명하게(0.8)
    line1 = ax.plot(close_prices.index, close_prices, color=MAIN_COLOR, linewidth=1.2, alpha=0.8, label='Price')
    ax.fill_between(close_prices.index, close_prices, bottom_limit, color=MAIN_COLOR, alpha=0.05)
    
    # 60일(약 3개월) 이동평균선: 더 얇게(1.0), 투명하게(0.8)
    line2 = ax.plot(close_prices.index, ma_60, color=MA_COLOR, linewidth=1.0, alpha=0.8, label='60-Day MA')
    
    # === 보조축(수익률) 추가 ===
    ax2 = ax.twinx()
    line3 = ax2.plot(close_prices.index, return_rates, color=RETURN_COLOR, linewidth=1.2, linestyle='--', alpha=0.7, label='Return Rate (%)')
    
    # 보조축 디자인 (초록색 텍스트, 테두리 제거)
    ax2.tick_params(axis='y', colors=RETURN_COLOR, labelsize=9, length=0, pad=10)
    for spine in ax2.spines.values():
        spine.set_visible(False)
    
    # 개별 차트 제목 가운데 정렬
    ax.set_title(name, fontsize=14, fontweight='normal', color=TEXT_COLOR, pad=15, loc='center')
    
    # 주축 불필요한 테두리(Spine) 완벽 제거
    for spine in ax.spines.values():
        spine.set_visible(False)
        
    # 부드러운 가로 눈금선만 추가 (주축 기준)
    ax.grid(axis='y', color=GRID_COLOR, linestyle='-', linewidth=1.5)
    ax.grid(axis='x', visible=False)
    
    # 축 라벨 디자인 단순화
    ax.tick_params(axis='both', which='major', labelsize=10, colors=SUB_TEXT_COLOR, length=0, pad=10)
    
    # X축 날짜 포맷 ('연도-월')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    
    # 범례 통합 (주축 + 보조축) 및 차트 밖 배치
    lines = line1 + line2 + line3
    labels = [l.get_label() for l in lines]
    # ncol=3 으로 세 가지 라벨을 한 줄로 정렬
    ax.legend(lines, labels, loc='lower right', bbox_to_anchor=(1.0, 1.0), frameon=False, fontsize=10, labelcolor=SUB_TEXT_COLOR, ncol=3)

# 여백 및 그래프 간 간격(h_pad) 조정 (위쪽 여백 rect 탑을 0.90으로 낮추어 노치 대비)
plt.tight_layout(rect=[0, 0.03, 1, 0.90], h_pad=5.0)
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
