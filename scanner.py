import yfinance as yf
import pandas as pd
import requests
import os
import time

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={'chat_id': CHAT_ID, 'text': message})
    except: pass

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def check_divergence(df):
    df = df.copy()
    df['RSI'] = calculate_rsi(df['Close'], period=14)
    df = df.dropna()
    
    df['Pivot_High'] = df['High'][(df['High'].shift(3) < df['High']) & 
                                  (df['High'].shift(2) < df['High']) & 
                                  (df['High'].shift(1) < df['High']) & 
                                  (df['High'].shift(-1) < df['High']) & 
                                  (df['High'].shift(-2) < df['High']) & 
                                  (df['High'].shift(-3) < df['High'])]
                                  
    df['Pivot_Low'] = df['Low'][(df['Low'].shift(3) > df['Low']) & 
                                (df['Low'].shift(2) > df['Low']) & 
                                (df['Low'].shift(1) > df['Low']) & 
                                (df['Low'].shift(-1) > df['Low']) & 
                                (df['Low'].shift(-2) > df['Low']) & 
                                (df['Low'].shift(-3) > df['Low'])]
    
    peaks = df[df['Pivot_High'].notna()]
    valleys = df[df['Pivot_Low'].notna()]
    
    is_div = False
    div_dir = None
    
    if len(peaks) >= 3:
        last_3 = peaks.iloc[-3:]
        if (last_3['High'].iloc[0] < last_3['High'].iloc[1] < last_3['High'].iloc[2]) and \
           (last_3['RSI'].iloc[0] > last_3['RSI'].iloc[1] > last_3['RSI'].iloc[2]):
            is_div, div_dir = True, "Sell"
            
    if len(valleys) >= 3:
        last_3 = valleys.iloc[-3:]
        if (last_3['Low'].iloc[0] > last_3['Low'].iloc[1] > last_3['Low'].iloc[2]) and \
           (last_3['RSI'].iloc[0] < last_3['RSI'].iloc[1] < last_3['RSI'].iloc[2]):
            is_div, div_dir = True, "Buy"
            
    return is_div, div_dir

def get_ob_signal(df, idx):
    score = 0
    direction = None
    body = abs(df['Close'].iloc[idx+1] - df['Open'].iloc[idx+1])
    range_hl = df['High'].iloc[idx+1] - df['Low'].iloc[idx+1]
    
    if range_hl == 0: return 0, None
        
    if body > range_hl * 0.6:
        score += 30
        if df['Close'].iloc[idx+1] > df['Open'].iloc[idx+1]:
            direction = "Buy"
            if df['Low'].iloc[idx+2] > df['High'].iloc[idx]: score += 25
            score += 20
            if df['Low'].iloc[idx] < df['Low'].iloc[idx-1]: score += 10
            score += 15
        elif df['Close'].iloc[idx+1] < df['Open'].iloc[idx+1]:
            direction = "Sell"
            if df['High'].iloc[idx+2] < df['Low'].iloc[idx]: score += 25
            score += 20
            if df['High'].iloc[idx] > df['High'].iloc[idx-1]: score += 10
            score += 15
            
    return score, direction

def find_recent_htf_ob(df):
    for i in range(-4, -20, -1):
        try:
            score, direction = get_ob_signal(df, i)
            if score >= 60:
                return score, direction, df['High'].iloc[i], df['Low'].iloc[i]
        except: pass
    return 0, None, 0, 0

def main():
    symbols = [
        "EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X", "AUDUSD=X", "USDCAD=X", "NZDUSD=X",
        "EURGBP=X", "EURJPY=X", "EURCHF=X", "EURAUD=X", "EURCAD=X", "EURNZD=X",
        "GBPJPY=X", "GBPCHF=X", "GBPAUD=X", "GBPCAD=X", "GBPNZD=X",
        "AUDJPY=X", "AUDCHF=X", "AUDCAD=X", "AUDNZD=X",
        "CADJPY=X", "CHFJPY=X", "NZDJPY=X", "NZDCHF=X", "NZDCAD=X"
    ]
    strategies = [
        {"htf_name": "4 ساعته (4H)", "htf_int": "4h", "htf_period": "20d", "ltfs": [{"name": "15 دقیقه", "int": "15m", "period": "5d"}, {"name": "5 دقیقه", "int": "5m", "period": "5d"}]},
        {"htf_name": "1 ساعته (1H)", "htf_int": "1h", "htf_period": "10d", "ltfs": [{"name": "15 دقیقه", "int": "15m", "period": "5d"}, {"name": "5 دقیقه", "int": "5m", "period": "5d"}]}
    ]

    for symbol in symbols:
        for strategy in strategies:
            try:
                df_htf = yf.Ticker(symbol).history(interval=strategy["htf_int"], period=strategy["htf_period"])
                if len(df_htf) < 20: continue
                
                ob_score, ob_dir, ob_high, ob_low = find_recent_htf_ob(df_htf)
                
                if ob_score >= 60:
                    current_close = df_htf['Close'].iloc[-1]
                    in_zone = False
                    if ob_dir == "Buy" and df_htf['Low'].iloc[-1] <= ob_high and current_close >= (ob_low * 0.999): in_zone = True
                    elif ob_dir == "Sell" and df_htf['High'].iloc[-1] >= ob_low and current_close <= (ob_high * 1.001): in_zone = True
                        
                    if in_zone:
                        for ltf in strategy["ltfs"]:
                            df_ltf = yf.Ticker(symbol).history(interval=ltf["int"], period=ltf["period"])
                            if len(df_ltf) < 20: continue
                            
                            is_div, div_dir = check_divergence(df_ltf)
                            if is_div and (div_dir == ob_dir):
                                clean_symbol = symbol.replace('=X', '')
                                ep1 = current_close
                                fibo_range = df_ltf['High'].iloc[-50:].max() - df_ltf['Low'].iloc[-50:].min()
                                
                                if ob_dir == "Sell":
                                    msg = (f"⚡️ سیگنال نوسان‌گیری با 2 پلن معاملاتی\n\nنماد: {clean_symbol}\nجهت: فروش 🔴\nبیس: {strategy['htf_name']} (امتیاز {ob_score})\nتایید: {ltf['name']}\n\n"
                                           f"📊 **پلن درصدی**\nورود 1: {ep1:.5f}\nورود 2: {ep1*1.005:.5f}\nورود 3: {ep1*1.0125:.5f}\nورود 4: {ep1*1.0225:.5f}\nتارگت: {ep1*0.995:.5f}\n\n"
                                           f"📈 **پلن فیبوناچی**\nورود 1: {ep1:.5f}\nورود 2: {ep1+(fibo_range*0.236):.5f}\nورود 3: {ep1+(fibo_range*0.382):.5f}\nورود 4: {ep1+(fibo_range*0.618):.5f}\nتارگت: {ep1-(fibo_range*0.618):.5f}")
                                else:
                                    msg = (f"⚡️ سیگنال نوسان‌گیری با 2 پلن معاملاتی\n\nنماد: {clean_symbol}\nجهت: خرید 🟢\nبیس: {strategy['htf_name']} (امتیاز {ob_score})\nتایید: {ltf['name']}\n\n"
                                           f"📊 **پلن درصدی**\nورود 1: {ep1:.5f}\nورود 2: {ep1*0.995:.5f}\nورود 3: {ep1*0.9875:.5f}\nورود 4: {ep1*0.9775:.5f}\nتارگت: {ep1*1.005:.5f}\n\n"
                                           f"📈 **پلن فیبوناچی**\nورود 1: {ep1:.5f}\nورود 2: {ep1-(fibo_range*0.236):.5f}\nورود 3: {ep1-(fibo_range*0.382):.5f}\nورود 4: {ep1-(fibo_range*0.618):.5f}\nتارگت: {ep1+(fibo_range*0.618):.5f}")
                                
                                send_telegram_message(msg)
                                break 
            except: pass
            time.sleep(1)

if __name__ == "__main__":
    main()
