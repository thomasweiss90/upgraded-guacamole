import os
import time
import math
import requests
import yfinance as yf
from datetime import datetime

BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
CHANNEL_ID = os.environ['TELEGRAM_CHANNEL_ID']

def is_valid_number(n):
    if n is None:
        return False
    if isinstance(n, float):
        return not (math.isnan(n) or math.isinf(n))
    return True

def fetch_with_retry(url, max_retries=3, delay=2):
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 200:
                return resp.json()
            time.sleep(delay * (attempt + 1))
        except:
            if attempt == max_retries - 1:
                return None
            time.sleep(delay * (attempt + 1))
    return None

def get_volume_data():
    for attempt in range(3):
        try:
            time.sleep(1)
            btc_data = fetch_with_retry("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd")
            if not btc_data:
                continue
            btc_price = btc_data['bitcoin']['usd']
            
            time.sleep(1)
            kraken = fetch_with_retry("https://api.coingecko.com/api/v3/exchanges/kraken")
            time.sleep(1)
            coinbase = fetch_with_retry("https://api.coingecko.com/api/v3/exchanges/gdax")
            
            if kraken and coinbase:
                kraken_vol = kraken.get('trade_volume_24h_btc', 0) * btc_price
                coinbase_vol = coinbase.get('trade_volume_24h_btc', 0) * btc_price
                
                if kraken_vol > 0 and coinbase_vol > 0:
                    return {
                        'kraken_vol': kraken_vol,
                        'coinbase_vol': coinbase_vol
                    }
        except:
            time.sleep(3)
    return None

def get_stock_data():
    ticker = yf.Ticker("COIN")
    
    for period in ['2d', '5d', '1mo']:
        try:
            hist = ticker.history(period=period)
            if not hist.empty and len(hist) >= 2:
                closes = hist['Close'].dropna()
                if len(closes) >= 2:
                    current = closes.iloc[-1]
                    previous = closes.iloc[-2]
                    if is_valid_number(current) and is_valid_number(previous):
                        change = ((current - previous) / previous) * 100
                        info = ticker.info
                        market_cap = info.get('marketCap') or info.get('enterpriseValue') or 0
                        return {
                            'price': current,
                            'change': change,
                            'market_cap': market_cap
                        }
        except:
            continue
    
    try:
        info = ticker.info
        price = (info.get('regularMarketPrice') or 
                info.get('currentPrice') or 
                info.get('previousClose'))
        prev_close = (info.get('regularMarketPreviousClose') or 
                     info.get('previousClose'))
        market_cap = info.get('marketCap') or info.get('enterpriseValue') or 0
        
        if is_valid_number(price) and is_valid_number(prev_close) and prev_close > 0:
            change = ((price - prev_close) / prev_close) * 100
            return {
                'price': price,
                'change': change,
                'market_cap': market_cap
            }
        elif is_valid_number(price):
            return {
                'price': price,
                'change': 0.0,
                'market_cap': market_cap
            }
    except:
        pass
    
    return None

def format_millions(num):
    if not is_valid_number(num):
        return "N/A"
    return f"${num/1e6:.2f}M"

def format_billions(num):
    if not is_valid_number(num):
        return "N/A"
    return f"${num/1e9:.2f}B"

def build_message(volume_data, stock_data):
    if not volume_data:
        return None
    
    kraken_vol = volume_data['kraken_vol']
    coinbase_vol = volume_data['coinbase_vol']
    ratio = kraken_vol / coinbase_vol
    percentage = ratio * 100
    
    sections = []
    
    # Header
    sections.append(f"📊 Kraken/Coinbase Daily Report — {datetime.utcnow().strftime('%Y-%m-%d')}\n")
    
    # Volume Section
    vol_section = f"""💹 24h Volume
Kraken:   {format_millions(kraken_vol)}
Coinbase: {format_millions(coinbase_vol)}
📈 Kraken is at {percentage:.2f}% of Coinbase 24h volume"""
    sections.append(vol_section)
    
    # Stock Section
    if stock_data and is_valid_number(stock_data['price']):
        price = stock_data['price']
        change = stock_data['change'] if is_valid_number(stock_data['change']) else 0
        market_cap = stock_data['market_cap']
        
        change_str = f"+{change:.2f}%" if change >= 0 else f"{change:.2f}%"
        emoji = "🟢" if change >= 0 else "🔴"
        
        stock_section = f"""\n💰 COIN Market Data
Price: ${price:.2f} {emoji} {change_str}"""
        
        if is_valid_number(market_cap) and market_cap > 0:
            stock_section += f"\nMarket Cap: {format_billions(market_cap)}"
            
            # ADD THE STOCK SECTION NOW
            sections.append(stock_section)
            
            implied = ratio * market_cap
            val_section = f"""\n🎯 Volume-Based Valuation
Implied Kraken Value: {format_billions(implied)}"""
            sections.append(val_section)
            
            # Summary sentence
            summary = f"""\nKraken's 24h volume is {format_millions(kraken_vol)} which is {percentage:.2f}% of Coinbase. Using only volume as a valuation indicator, this equals to a Kraken valuation of {format_billions(implied)} compared to Coinbases current {format_billions(market_cap)} market cap."""
            sections.append(summary)
        else:
            sections.append(stock_section)
    else:
        sections.append(f"\n📊 Stock data temporarily unavailable. Kraken volume is {format_millions(kraken_vol)} ({percentage:.2f}% of Coinbase 24h volume).")
    
    return "\n".join(sections)

def post():
    volume_data = get_volume_data()
    
    if not volume_data:
        print("No volume data. Skipping post.")
        return
    
    stock_data = get_stock_data()
    message = build_message(volume_data, stock_data)
    
    if not message:
        return
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    try:
        response = requests.post(url, json={
            'chat_id': CHANNEL_ID,
            'text': message,
            'disable_notification': True
        }, timeout=15)
        
        if response.status_code == 200:
            print("Posted successfully")
    except Exception as e:
        print(f"Failed to post: {e}")

if __name__ == "__main__":
    post()
