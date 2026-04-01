# -*- coding: utf-8 -*-
import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import json
import time

# --- 1. 固定設定區 ---
FIXED_LINE_TOKEN = "p0hZsq9njQwsK2QYkeTQjYYyJ87MpttosPY8E7e6HIbJns3Ii2AnYj4Z+QNaGCVrDphhuFlGKHJCnfMleQ1XlCJj2FRu2UJTYj9dAZUFIZfB4SLcVjXncnsGLrpflCwc1O3bU4OotJqW3zeslTFk8QdB04t89/1O/w1cDnyilFU="
FIXED_USER_ID = "Ud25e9519467182c8b844df5260bccde5"

# --- 2. 核心邏輯函數 ---

def calculate_v5_score(df):
    try:
        if len(df) < 30: return 0, None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df['EMA12'] = ta.ema(df['Close'], length=12)
        df['EMA26'] = ta.ema(df['Close'], length=26)
        df['MA5'] = ta.sma(df['Close'], length=5)    
        df['MA20'] = ta.sma(df['Close'], length=20)  
        
        macd = ta.macd(df['Close'])
        df['MACD'] = macd['MACD_12_26_9']
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        score = 0
        now = df.iloc[-1]
        
        if now['Close'] > now['EMA12']: score += 30
        if now['EMA12'] > now['EMA26']: score += 30
        if now['MACD'] > 0: score += 20
        if 50 < now['RSI'] < 70: score += 20
        
        return score, now
    except:
        return 0, None

def send_line_message(message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {FIXED_LINE_TOKEN}"}
    payload = {"to": FIXED_USER_ID, "messages": [{"type": "text", "text": message}]}
    try:
        requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
    except:
        pass

# --- 3. 介面設計 ---

st.set_page_config(page_title="V7.1 國發級線圖增強版", layout="wide")
st.title("📈 V7.1 國發級全台股掃描器 (含即時線圖)")

# 側邊欄狀態
st.sidebar.header("🛠️ 系統狀態")
st.sidebar.success("✅ LINE 授權已自動載入")

# 擴充後的權值股清單
ALL_TW_STOCKS = ["2330","2317","2454","2303","2382","3231","2603","2609","2615","2618","2610","2357","2353","2324","2301","2376","2377","2408","2409","3481","3037","3034","2379","6239","2881","2882","2886","2891","2884","2885","5880","2892","2880","2883","2887","2890","1101","1102","1301","1303","1326","6505","2005","2105","2201","2207","2912","5903","9904","9910"]

# --- 4. 掃描執行邏輯 ---

def run_scanner(target_list, is_full_scan=False):
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total = len(target_list)
    for i, ticker in enumerate(target_list):
        status_text.text(f"正在掃描 ({i+1}/{total}): {ticker}")
        progress_bar.progress((i + 1) / total)
        
        # 判斷是否為櫃買股票 (簡單邏輯：代碼長度或特定清單，此處預設為上市)
        data = yf.download(f"{ticker}.TW", period="8mo", progress=False)
        if data.empty: continue

        score, now = calculate_v5_score(data)
        if now is not None and score >= 75:
            now_price = float(now['Close'])
            ma5 = float(now['MA5'])
            ma20 = float(now['MA20'])
            
            # 建立 Yahoo 股市線圖連結 (包含即時 K 線圖)
            chart_url = f"https://tw.stock.yahoo.com/quote/{ticker}.TW"
            
            res = {
                "代碼": ticker,
                "評分": score,
                "現價": round(now_price, 2),
                "5MA": round(ma5, 2),
                "20MA": round(ma20, 2)
            }
            results.append(res)
            
            # 根據 5MA 狀態決定訊息圖示
            ma5_status = "🟢 已站上 5MA" if now_price > ma5 else "🟡 低於 5MA (等待轉強)"
            
            # 組合 LINE 訊息
            msg = f"""🚨【波段監控報告】
標的：{ticker}
評分：{score} 分
現價：{now_price:.2f}
狀態：{ma5_status}
------------------
🛡️ 停損參考：{now_price*0.93:.2f}
⚓ 生命線(20MA)：{ma20:.2f}

📊 即時線圖查看：
{chart_url}"""
            
            send_line_message(msg)
        
        if is_full_scan:
