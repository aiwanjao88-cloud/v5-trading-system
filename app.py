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
        if len(df) < 35: return 0, None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.astype(float)
        
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

st.set_page_config(page_title="V7.4 國際全域掃描器", layout="wide")
st.title("📈 V7.4 國際全域掃描器 (台美股連動版)")

# 預設清單
PENNY_STOCKS = ["2344","2363","2409","3481","6116","2618","2610","2883","1605","1609","2002","2353","2641"]
US_STOCKS = ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA", "AMZN", "META", "AMD", "NFLX", "COIN", "PLTR", "SOFI", "U"]

# --- 4. 掃描執行邏輯 ---

def run_scanner(target_list, mode_name="台股"):
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total = len(target_list)
    for i, ticker in enumerate(target_list):
        status_text.text(f"[{mode_name}] 正在分析: {ticker} ({i+1}/{total})")
        progress_bar.progress((i + 1) / total)
        
        # 根據模式決定代碼格式
        if mode_name == "美股":
            full_ticker = ticker
            chart_url = f"https://finance.yahoo.com/quote/{ticker}"
        else:
            # 台股自動嘗試上市/上櫃
            full_ticker = f"{ticker}.TW"
            data = yf.download(full_ticker, period="8mo", progress=False)
            if data.empty:
                full_ticker = f"{ticker}.TWO"
            chart_url = f"https://tw.stock.yahoo.com/quote/{ticker}"

        data = yf.download(full_ticker, period="8mo", progress=False)
        if data.empty: continue

        score, now = calculate_v5_score(data)
        if now is not None:
            now_price = float(now['Close'])
            ma5 = float(now['MA5'])
            ma20 = float(now['MA20'])
            
            # 門檻邏輯 (美股不限價格，台股小資限 10-60)
            threshold = 80 if mode_name in ["小資飆股", "美股"] else 75
            
            if score >= threshold and now_price > ma5:
                results.append({"代碼": ticker, "評分": score, "現價": round(now_price, 2), "20MA": round(ma20, 2)})
                
                currency = "USD" if mode_name == "美股" else "TWD"
                msg = f"🌟【{mode_name}強勢訊號】\n標的：{ticker}\n評分：{score} 分\n價格：{now_price:.2f} {currency}\n------------------\n💡 短線噴發中，站穩5MA！\n⚓ 出場參考(20MA)：{ma20:.2f}\n📊 即時看圖：{chart_url}"
                send_line_message(msg)
        
        time.sleep(0.2)
            
    status_text.text("✅ 掃描任務完成！")
    return results

# --- 5. 按鈕區 ---
row1_col1, row1_col2 = st.columns(2)
row2_col1, row2_col2 = st.columns(2)

with row1_col1:
    if st.button("🔍 啟動權值股掃描 (台股)"):
        res = run_scanner(["2330","2317","2454","2303","2382","3231","2603"], "權值股")
        if res: st.table(pd.DataFrame(res))

with row1_col2:
    if st.button("🔥 啟動小資飆股偵測 (台股)"):
        res = run_scanner(PENNY_STOCKS, "小資飆股")
        if res: st.table(pd.DataFrame(res))

with row2_col1:
    if st.button("🇺🇸 啟動美股飆股偵測"):
        with st.spinner("美股數據載入中..."):
            res = run_scanner(US_STOCKS, "美股")
            if res: st.table(pd.DataFrame(res))
            else: st.warning("目前美股無符合條件標的。")

with row2_col2:
    custom_input = st.text_input("自選代碼 (台美股混搭)", "TSLA,NVDA,2330")
    if st.button("🚀 執行混搭掃描"):
        # 簡單判斷：純數字為台股，英文為美股
        custom_list = [t.strip() for t in custom_input.split(",") if t.strip()]
        res = run_scanner(custom_list, "混搭")
        if res: st.table(pd.DataFrame(res))
