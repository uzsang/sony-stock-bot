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

# 1년 전 환율을 기준(a)으로 퍼센트 데이터 생성
krw_data = yf.download('KRW=X', period='1y')
base_exchange_rate = float(krw_data['Close'].iloc[0]) # 1년 전 오늘의 환율 (a)
krw_pct = (krw_data['Close'] / base_exchange_rate) * 100 # (각 일자 환율 / a) * 100

# 3개의 서브플롯 생성
fig, axes = plt.subplots(3, 1, figsize=(10, 12))
today_str = datetime.now().strftime("%Y-%m-%d")
fig.suptitle(f'Market 1-Year Trend & USD/KRW Rate ({today_str})', fontsize=16)

for ax, (name, ticker) in zip(axes, tickers.items()):
    # 주가 데이터 다운로드 및 3개월(60일) 이동평균선 계산
    data = yf.download(ticker, period='1y')
    data['3M_MA'] = data['Close'].rolling(window=60).mean()
    
    # [왼쪽 Y축] 종가 및 3개월 이동평균선 시각화
    line1 = ax.plot(data.index, data['Close'], label='Close Price', color='tab:blue', alpha=0.6)
    line2 = ax.plot(data.index, data['3M_MA'], label='3-Month MA', color='tab:orange', linewidth=2)
    ax.set_title(name)
    ax.set_ylabel('Price')
    ax.grid(True, linestyle='--', alpha=0.6)
    
    # [오른쪽 Y축] 환율 변동 비율 시각화 (점선)
    ax2 = ax.twinx()
    line3 = ax2.plot(krw_pct.index, krw_pct, label=f'USD/KRW % (Base: {base_exchange_rate:.1f}원)', color='tab:green', linestyle='--', alpha=0.8)
    ax2.set_ylabel('Exchange Rate (%)')
    
    # 양쪽 Y축의 범례(Legend)를 하나로 묶어서 표시
    lines = line1 + line2 + line3
    labels = [l.get_label() for l in lines]
    ax.legend(lines, labels, loc='upper left')

# 레이아웃 간격 조정 및 이미지 저장
plt.tight_layout()
image_path = 'stock_chart_with_krw.png'
plt.savefig(image_path)

# 텔레그램으로 이미지 전송
url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
with open(image_path, 'rb') as photo:
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'caption': f'📊 주요 지수 및 환율 1년치 차트입니다. ({today_str})\n초록색 점선은 1년 전 환율({base_exchange_rate:.1f}원) 대비 현재 비율입니다.'
    }
    requests.post(url, data=payload, files={'photo': photo})
