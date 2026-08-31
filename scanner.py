import yfinance as yf
import pandas as pd
import requests
import os
import time

# دریافت اطلاعات اکانت اول
TELEGRAM_TOKEN_1 = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID_1 = os.environ.get('CHAT_ID')

# دریافت اطلاعات اکانت دوم
TELEGRAM_TOKEN_2 = os.environ.get('TELEGRAM_TOKEN_2')
CHAT_ID_2 = os.environ.get('CHAT_ID_2')

def send_telegram_message(message):
    # لیست اکانت‌ها برای ارسال همزمان
    accounts = [
        (TELEGRAM_TOKEN_1, CHAT_ID_1),
        (TELEGRAM_TOKEN_2, CHAT_ID_2)
    ]
    
    for token, chat_id in accounts:
        if token and chat_id:  # چک می‌کند که اگر اطلاعات وارد شده بود، پیام را بفرستد
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            try:
                requests.post(url, data={'chat_id': chat_id, 'text': message})
            except: 
                pass

# ==========================================
# بقیه کدهای ربات (مثل توابع RSI و main) دقیقاً در ادامه اینجا باقی می‌مانند...
