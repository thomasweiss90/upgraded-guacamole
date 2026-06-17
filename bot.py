import os
import time
import requests
import yfinance as yf
from datetime import datetime

BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
CHANNEL_ID = os.environ['TELEGRAM_CHANNEL_ID']

def format_currency(num):
    """Format number with $ and commas, 2 decimal places"""
    return f"${num:,.2f}"

def compact_format(num):
    """Compact format for the summary sentence ($1.36B or $938.65M)"""
    if num >= 1e9:
        return f"${num/1e9:.2f}B"
    elif num >= 1e6:
        return f"${num/1e6:.2f}M"
    else:
        return f"${num:.2f}"

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

def format_message(data):
    if not data:
        return "⚠️ Daily metrics unavailable"
    
    kraken_vol = data['kraken_vol']
    coinbase_vol = data['coinbase_vol']
    market_cap = data['market_cap']
    
    # Precise calculations (no rounding until display)
    ratio_decimal = kraken_vol / coinbase_vol if coinbase_vol > 0 else 0
    percentage = ratio_decimal * 100
    implied_valuation = ratio_decimal * market_cap
    
    # Change emoji
    change_str = f"+{data['coin_change']:.2f}%" if data['coin_change'] >= 0 else f"{data['coin_change']:.2f}%"
    change_emoji = "🟢" if data['coin_change'] >= 0 else "🔴"
    
    msg = f"""📊 Kraken/Coinbase Daily Report — {datetime.utcnow().strftime('%Y-%m-%d')}

💹 24h Volume (USD)
Kraken:   {format_currency(kraken_vol)}
Coinbase: {format_currency(coinbase_vol)}
📈 Kraken is {percentage:.2f}% of Coinbase volume

💰 COIN Market Data
Price: ${data['coin_price']:.2f} {change_emoji} {change_str}
Market Cap: {format_currency(market_cap)}

🎯 Volume-Based Valuation
Implied Kraken Value: {format_currency(implied_valuation)}

Kraken's 24h volume is {compact_format(kraken_vol)} which is {percentage:.2f}% of Coinbase. Using only volume as a valuation indicator, this equals to a Kraken valuation of {compact_format(implied_valuation)} compared to Coinbases current {compact_format(market_cap)} market cap."""
    
    return msg

def post():
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = fetch_data()
    message = format_message(data)
    
    response = requests.post(url, json={
        'chat_id': CHANNEL_ID,
        'text': message,
        'disable_notification': True
    }, timeout=10)
    
    print(f"Response: {response.status_code}")

if __name__ == "__main__":
    post()
