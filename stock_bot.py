import os
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression
import requests

# GitHub Actions Secrets에서 텔레그램 토큰 및 챗 ID 로드
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

def fetch_data(ticker="SONY", period="1y"):
    """야후 파이낸스에서 주가 데이터를 가져오고 필요한 이동평균선만 계산합니다."""
    df = yf.download(ticker, period=period)
    
    # 200일 이동평균선 제거됨
    # 50일 이동평균선만 계산
    df['50_MA'] = df['Close'].rolling(window=50).mean()
    
    # 결측치 제거
    df = df.dropna()
    return df

def predict_price(df):
    """scikit-learn을 이용해 내일의 주가를 간단히 예측합니다."""
    # 날짜를 연속된 숫자로 변환하여 학습 데이터로 사용
    df = df.copy()
    df['Days'] = np.arange(len(df))
    
    X = df[['Days']]
    y = df['Close']
    
    model = LinearRegression()
    model.fit(X, y)
    
    # 다음 날(len(df)) 예측
    next_day = pd.DataFrame({'Days': [len(df)]})
    predicted_price = model.predict(next_day)[0]
    
    return predicted_price

def plot_chart(df, ticker="SONY"):
    """matplotlib을 사용하여 가격과 50일 이동평균선을 시각화합니다."""
    plt.figure(figsize=(10, 6))
    
    # 실제 주가 및 50일선 플로팅 (200일선 제외)
    plt.plot(df.index, df['Close'], label='Close Price', color='blue', linewidth=1.5)
    plt.plot(df.index, df['50_MA'], label='50-Day MA', color='orange', linestyle='--')
    
    plt.title(f'{ticker} Stock Price History')
    plt.xlabel('Date')
    plt.ylabel('Price (USD)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 이미지 파일로 저장
    chart_path = 'stock_chart.png'
    plt.savefig(chart_path, bbox_inches='tight')
    plt.close()
    
    return chart_path

def send_telegram_notification(message, image_path):
    """텔레그램 봇 API를 통해 텍스트와 차트 이미지를 전송합니다."""
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("Error: TELEGRAM_TOKEN 또는 CHAT_ID가 설정되지 않았습니다.")
        return

    # 1. 텍스트 메시지 전송
    text_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(text_url, data={'chat_id': CHAT_ID, 'text': message})
    
    # 2. 차트 이미지 전송
    photo_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    with open(image_path, 'rb') as photo:
        requests.post(photo_url, data={'chat_id': CHAT_ID}, files={'photo': photo})

def main():
    ticker = "SONY"
    
    # 1. 데이터 수집
    df = fetch_data(ticker)
    
    # 2. 모델 훈련 및 가격 예측
    predicted_price = predict_price(df)
    current_price = float(df['Close'].iloc[-1])
    
    # 3. 차트 생성
    chart_path = plot_chart(df, ticker)
    
    # 4. 텔레그램 메시지 포맷팅 및 발송
    message = (
        f"📊 {ticker} 자동 주가 분석\n\n"
        f"▪️ 현재가: ${current_price:.2f}\n"
        f"▪️ AI 예측가(내일): ${predicted_price:.2f}\n\n"
        f"* 200일 이동평균선이 차트에서 제거되었습니다."
    )
    
    send_telegram_notification(message, chart_path)
    print("알림 전송이 완료되었습니다.")

if __name__ == "__main__":
    main()
