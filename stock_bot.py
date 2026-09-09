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
MAIN_COLOR = '#1A73E8'     
MA_COLOR = '#FF9500'       
RETURN_COLOR = '#34A853'   
TEXT_COLOR = '#202124'  
SUB_TEXT_COLOR = '#5F6368' 
BG_COLOR = '#FFFFFF'    
GRID_COLOR = '#F1F3F4'  
VERTICAL_GRID_COLOR = '#E8EAED' 

fig, axes = plt.subplots(3, 1, figsize=(9, 12.5), facecolor=BG_COLOR)
today_str = datetime.now().strftime("%Y-%m-%d")

fig.suptitle('Market Overview', fontsize=22, fontweight='medium', color=TEXT_COLOR, y=0.985)
fig.text(0.5, 0.958, f'Korean Listed US ETFs 3-Year Trend ({today_str})', 
         ha='center', fontsize=12, color=SUB_TEXT_COLOR)

for ax, (name, ticker) in zip(axes, tickers.items()):
    ax.set_facecolor(BG_COLOR)
    
    data = yf.download(ticker, period='3y')
    close_prices = data['Close'].squeeze()
    
    ma_60 = close_prices.rolling(window=60).mean()
    
    current_price = close_prices.iloc[-1]
    return_rates = (current_price - close_prices) / close_prices * 100
    
    min_price = close_prices.min()
    max_price = close_prices.max()
    padding = (max_price - min_price) * 0.1
    bottom_limit = min_price - padding
    ax.set_ylim(bottom_limit, max_price + padding)
    
    line1 = ax.plot(close_prices.index, close_prices, color=MAIN_COLOR, linewidth=1.2, alpha=0.8, label='Price')
    ax.fill_between(close_prices.index, close_prices, bottom_limit, color=MAIN_COLOR, alpha=0.05)
    
    line2 = ax.plot(close_prices.index, ma_60, color=MA_COLOR, linewidth=1.0, alpha=0.8, label='60-Day MA')
    
    ax2 = ax.twinx()
    line3 = ax2.plot(close_prices.index, return_rates, color=RETURN_COLOR, linewidth=0.5, linestyle='--', alpha=0.8, label='Return Rate (%)')
    
    ax2.tick_params(axis='y', colors=SUB_TEXT_COLOR, labelsize=10, length=0, pad=10)
    for spine in ax2.spines.values():
        spine.set_visible(False)
    
    ax.set_title(name, fontsize=12, fontweight='normal', color=TEXT_COLOR, pad=6, loc='center', linespacing=1.2)
    
    lines = line1 + line2 + line3
    labels = [l.get_label() for l in lines]
    ax.legend(lines, labels, loc='lower center', frameon=True, facecolor=BG_COLOR, edgecolor='none', fontsize=8, labelcolor=SUB_TEXT_COLOR, ncol=3)
    
    for spine in ax.spines.values():
        spine.set_visible(False)
        
    ax.grid(axis='y', color=GRID_COLOR, linestyle='-', linewidth=1.5)
    ax.grid(axis='x', color=VERTICAL_GRID_COLOR, linestyle='--', linewidth=0.8, alpha=0.7)
    
    ax.tick_params(axis='both', which='major', labelsize=10, colors=SUB_TEXT_COLOR, length=0, pad=10)
    
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right')

plt.tight_layout(rect=[0, 0.01, 1, 0.945], h_pad=2.8)
image_path = 'tiger_etf_modern.png'
plt.savefig(image_path, dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor())

url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
with open(image_path, 'rb') as photo:
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'caption': f'📊 오늘의 주식 시장 요약입니다. ({today_str})\n파란선: 현재가 / 주황선: 60일 이평선 / 초록점선: 해당 일 매수 시 현재 수익률(%)'
    }
    requests.post(url, data=payload, files={'photo': photo})
