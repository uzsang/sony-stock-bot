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
MAIN_COLOR = '#1A73E8'  # 구글 톤의 맑은 파란색
MA_COLOR = '#FF9500'    # 애플 톤의 직관적인 오렌지색
TEXT_COLOR = '#202124'  # 진한 흑회색
SUB_TEXT_COLOR = '#5F6368' # 부드러운 회색
BG_COLOR = '#FFFFFF'    # 순백색 배경
GRID_COLOR = '#F1F3F4'  # 연한 눈금선

fig, axes = plt.subplots(3, 1, figsize=(10, 15), facecolor=BG_COLOR)
today_str = datetime.now().strftime("%B %d, %Y")

# 전체 제목 (1-Year -> 3-Year 로 변경)
fig.suptitle('Market Overview', fontsize=24, fontweight='bold', color=TEXT_COLOR, y=0.95)
fig.text(0.5, 0.92, f'Korean Listed US ETFs 3-Year Trend ({today_str})', 
         ha='center', fontsize=12, color=SUB_TEXT_COLOR)

for ax, (name, ticker) in zip(axes, tickers.items()):
    ax.set_facecolor(BG_COLOR)
    
    # 3년치(3y) 데이터 다운로드
    data = yf.download(ticker, period='3y')
    
    # yfinance 다중 인덱스 반환 이슈 해결
    close_prices = data['Close'].squeeze()
    
    # 60일 이평선 계산
    ma_60 = close_prices.rolling(window=60).mean()
    
    # Y축 최소값/최대값 타이트하게 계산 (불필요한 밑공간 제거)
    min_price = close_prices.min()
    max_price = close_prices.max()
    padding = (max_price - min_price) * 0.1  # 위아래 10% 여백
    bottom_limit = min_price - padding
    ax.set_ylim(bottom_limit, max_price + padding)
    
    # 메인 주가 선 및 아래 영역 색칠 (하단 한계선까지 채움)
    ax.plot(close_prices.index, close_prices, color=MAIN_COLOR, linewidth=2.5, label='Price')
    ax.fill_between(close_prices.index, close_prices, bottom_limit, color=MAIN_COLOR, alpha=0.05)
    
    # 60일(약 3개월) 이동평균선
    ax.plot(close_prices.index, ma_60, color=MA_COLOR, linewidth=2, label='60-Day MA')
    
    # 개별 차트 제목 (왼쪽 위 정렬)
    ax.text(0.0, 1.05, name, transform=ax.transAxes, fontsize=14, fontweight='bold', color=TEXT_COLOR)
    
    # 불필요한 테두리(Spine) 완벽 제거
    for spine in ax.spines.values():
        spine.set_visible(False)
        
    # 부드러운 가로 눈금선만 추가
    ax.grid(axis='y', color=GRID_COLOR, linestyle='-', linewidth=1.5)
    ax.grid(axis='x', visible=False)
    
    # 축 라벨 디자인 단순화
    ax.tick_params(axis='both', which='major', labelsize=10, colors=SUB_TEXT_COLOR, length=0, pad=10)
    
    # X축 날짜 포맷 및 간격 조정 (3년치이므로 6개월 간격으로 쾌적하게 표시)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    
    # 범례 디자인
    ax.legend(loc='upper right', frameon=False, fontsize=11, labelcolor=SUB_TEXT_COLOR)

# 여백 및 그래프 간 간격(h_pad) 시원하게 조정
plt.tight_layout(rect=[0, 0.03, 1, 0.90], h_pad=4.0)
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

