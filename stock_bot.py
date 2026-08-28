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
    """야후 파이낸스에서 주가 데이터를 가져오고 60일 이동평균선을 계산합니다."""
    df = yf.download(ticker, period=period)
    
    # 60일 이동평균선 계산
    df['60_MA'] = df['Close'].rolling(window=60).mean()
    
    # 결측치 제거
    df = df.dropna()
    return df

def predict_price(df):
    """scikit-learn을 이용해 내일의 주가를 간단히 예측합니다."""
    df = df.copy()
    df['Days'] = np.arange(len(df))
    
    # .values를 사용하여 numpy 배열로 변환 (경고 방지)
    X = df[['Days']].values 
    y = df['Close'].values
    
    model = LinearRegression()
    model.fit(X, y)
    
    # 다음 날 예측 (단일 2D 배열로 전달)
    next_day_X = np.array([[len(df)]에러의 원인은 scikit-learn의 `predict()` 메서드가 단일 숫자가 아닌 NumPy 배열(예: `[85000.5]`)을 반환하기 때문입니다. 92번째 줄의 텔레그램 메시지 f-string에서 이 배열 객체에 `:.2f`나 `:,` 같은 숫자 포맷팅을 직접 적용하려고 시도하면서 `TypeError`가 발생했습니다.

**치명적 에러 해결 방법 (Line 92)**

f-string으로 포맷팅하기 전에 `[0]` 인덱스나 `.item()`을 사용하여 NumPy 배열에서 스칼라(단일 숫자) 값을 먼저 추출해야 합니다.

*수정 전 (에러 발생 추정 코드):*
```python
predicted_price = model.predict(X_new)
message = f"📊 {ticker} 자동 주가 분석\n\n예상가: {predicted_price:,.0f}원"
