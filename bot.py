import os
import time
import requests
import yfinance as yf
from datetime import datetime

BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
CHANNEL_ID = os.environ['TELEGRAM_CHANNEL_ID']

def fetch_data():
    try:
        time.sleep(1)
        btc = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=10).json()
        btc_price = btc['bitcoin']['usd']
        
        time.sleep(1)
        kraken = requests.get("https://api.coingecko.com/api/v3/exchanges/kraken", timeout=10).json()
        
        time.sleep(1)
        coinbase = requests.get("https://api.coingecko.com/api/v3/exchanges/gdax", timeout=10).json()
        
        kraken_vol = kraken.get('trade_volume_24h_btc', 0) * btc_price
        coinbase_vol = coinbase.get('trade_volume_24h_btc', 0) * btc_price
        
        if kraken_vol == 0 or coinbase_vol == 0:
            return None
            
        coin = yf.Ticker("COIN")
        info = coin.info
        hist = coin.history(period="2d")
        
        stock_price = hist['Close'].iloc[-1]
        market_cap = info.get('marketCap', 0)
        prev_close = hist['Close'].iloc[-2]
        daily_change = ((stock_price - prev_close) / prev_close) * 100
        
        return {
            'kraken_vol': kraken_vol,
            'coinbase_vol': coinbase_vol,
            'coin_price': stock_price,
            'coin_change': daily_change,
            'market_cap': market_cap
        }
    except Exception as e:
        print(f"Error: {e}")
        return None

def format_billions(num):
    return f"${num/1e9:.2f}B" if num >= 1e9 else f"${num/1e6:.1f}M"

def format_message(data):
    if not data:
        return "Daily metrics unavailable"
    
    ratio = data['kraken_vol'] / data['coinbase_vol'] if data['coinbase_vol'] > 0 else 0
    implied_kraken_val = ratio * data['market_cap'] if ratio > 0 else 0
    change_str = f"+{data['coin_change']:.1f}%" if data['coin_change'] >= 0 else f"{data['coin_change']:.1f}%"
    
    return f"""Kraken/Coinbase Daily Report ({datetime.utcnow().strftime('%Y-%m-%d')})

Volumes (24h):
Kraken:   {format_billions(data['kraken_vol'])}
Coinbase: {format_billions(data['coinbase_vol'])}
K/C Ratio: 1:{1/ratio:.1f}

COIN: ${data['coin_price']:.2f} ({change_str}) | Cap: {format_billions(data['market_cap'])}

Implied Kraken Valuation: {format_billions(implied_kraken_val)}"""

def post():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = fetch_data()
    
    requests.post(url, json={
        'chat_id': CHANNEL_ID,
        'text': format_message(data),
        'disable_notification': True
    }, timeout=10)

if __name__ == "__main__":
    post()
