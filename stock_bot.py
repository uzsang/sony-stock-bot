import yfinance as yf
import matplotlib.pyplot as plt
import requests
import os
from datetime import datetime

# 환경 변수에서 텔레그램 토큰 및 챗 ID 불러오기
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# 조회할 티커 심볼 (한국 상장 TIGER ETF 시리즈)
tickers = {
    'TIGER US S&P 500': '360750.KS', 
    'TIGER US NASDAQ 100': '133690.KS', 
    'TIGER US Dividend Dow Jones (SCHD)': '458730.KS'
}

# 3개의 서브플롯 생성
fig, axes = plt.subplots(3, 1, figsize=(10, 12))
today_str = datetime.now().strftime("%Y-%m-%d")
fig.suptitle(f'Korean Listed US ETFs 1-Year Trend ({today_str})', fontsize=16)

for ax, (name, ticker) in zip(axes, tickers.items()):
    # 최근 1년치 데이터 다운로드
    data = yf.download(ticker, period='1y')
    
    # 3개월(약 60 거래일) 이동평균선 계산
    data['3M_MA'] = data['Close'].rolling(window=60).mean()
    
    # 종가(Close)와 3개월 이동평균선(3M_MA) 시각화
    ax.plot(data.index, data['Close'], label='Close Price', color='tab:blue', alpha=0.6)
    ax.plot(data.index, data['3M_MA'], label='3-Month MA', color='tab:orange', linewidth=2)
    
    ax.set_title(name)
    ax.set_ylabel('Price (KRW)')
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.legend(loc='upper left')

# 레이아웃 간격 조정 및 이미지 저장
plt.tight_layout()
image_path = 'tiger_etf_chart.png'
plt.savefig(image_path)

# 텔레그램으로 이미지 전송
url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
with open(image_path, 'rb') as photo:
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'caption': f'📊 국내 상장 미국 ETF 1년치 차트입니다. ({today_str})\n파란선: 현재가 / 주황선: 3개월(60일) 이동평균선\n\n*환율이 이미 반영된 원화(KRW) 기준 가격입니다.'
    }
    requests.post(url, data=payload, files={'photo': photo})
