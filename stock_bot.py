import yfinance as yf
import matplotlib.pyplot as plt
import requests
import os
from datetime import datetime

# 환경 변수에서 텔레그램 토큰 및 챗 ID 불러오기
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# 조회할 티커 심볼
tickers = {
    'S&P 500': '^GSPC', 
    'Nasdaq 100': '^NDX', 
    'SCHD': 'SCHD'
}

# 3개의 서브플롯 생성
fig, axes = plt.subplots(3, 1, figsize=(10, 12))
today_str = datetime.now().strftime("%Y-%m-%d")
fig.suptitle(f'Market 1-Year Trend with 3-Month MA ({today_str})', fontsize=16)

for ax, (name, ticker) in zip(axes, tickers.items()):
    # 최근 1년치 데이터 다운로드
    data = yf.download(ticker, period='1y')
    
    # 3개월(약 60 거래일) 이동평균선 계산
    data['3M_MA'] = data['Close'].rolling(window=60).mean()
    
    # 종가(Close)와 3개월 이동평균선(3M_MA) 시각화
    ax.plot(data.index, data['Close'], label='Close Price', color='tab:blue', alpha=0.6)
    ax.plot(data.index, data['3M_MA'], label='3-Month MA', color='tab:orange', linewidth=2)
    
    ax.set_title(name)
    ax.set_ylabel('Price')
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.legend()

# 레이아웃 간격 조정 및 이미지 저장
plt.tight_layout()
image_path = 'stock_chart_ma.png'
plt.savefig(image_path)

# 텔레그램으로 이미지 전송
url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
with open(image_path, 'rb') as photo:
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'caption': f'📊 주요 지수 및 ETF 1년치 차트입니다. ({today_str})\n주황색 선은 3개월(60일) 이동평균선입니다.'
    }
    requests.post(url, data=payload, files={'photo': photo})
