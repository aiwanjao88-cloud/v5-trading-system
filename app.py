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
        
        # 確保資料是 float 格式
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

st.set_page_config(page_title="V7.3 小資飆股終極版", layout="wide")
st.title("📈 V7.3 國發級掃描器 (加強版)")

# 擴充小資清單 (增加熱門銅板股)
PENNY_STOCKS = ["2344","2363","2409","3481","6116","2618","2610","2883","2888","1605","1608","1609","2002","2014","2323","2353","2362","2449","3035","3706","1904","2641","2312","2324","2406","3041","3062","6142"]

# --- 4. 掃描執行邏輯 ---

def run_scanner(target_list, mode_name="一般"):
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total = len(target_list)
    for i, ticker in enumerate(target_list):
        status_text.text(f"[{mode_name}] 正在診斷: {ticker} ({i+1}/{total})")
        progress_bar.progress((i + 1) / total)
        
        # 嘗試下載資料 (先試上市 .TW，若空則試上櫃 .TWO)
        data = yf.download(f"{ticker}.TW", period="8mo", progress=False)
        if data.empty:
            data = yf.download(f"{ticker}.TWO", period="8mo", progress=False)
        
        if data.empty: continue

        score, now = calculate_v5_score(data)
        if now is not None:
            now_price = float(now['Close'])
            ma5 = float(now['MA5'])
            ma20 = float(now['MA20'])
            
            # 過濾條件
            if mode_name == "小資飆股":
                if not (10 <= now_price <= 60) or score < 80: continue
            else:
                if score < 75: continue

            if now_price > ma5:
                chart_url = f"https://tw.stock.yahoo.com/quote/{ticker}"
                results.append({"代碼": ticker, "評分": score, "現價": round(now_price, 2), "20MA": round(ma20, 2)})
                
                msg = f"🔥【小資飆股訊號】\n標的：{ticker}\n評分：{score} 分\n價格：{now_price:.2f}\n------------------\n💡 短線轉強，站穩5MA！\n⚓ 出場參考(20MA)：{ma20:.2f}\n📊 即時看圖：{chart_url}"
                send_line_message(msg)
        
        # 增加延遲防封鎖
        time.sleep(0.2)
            
    status_text.text("✅ 掃描任務完成！")
    return results

# --- 5. 按鈕區 ---
col1, col2, col3 = st.columns(3)
with col1:
    user_input = st.text_input("自選清單", "2330,2317,2454")
    if st.button("🚀 執行自選掃描"):
        res = run_scanner([t.strip() for t in user_input.split(",") if t.strip()], "自選")
        if res: st.table(pd.DataFrame(res))
with col2:
    if st.button("🔍 權值股掃描"):
        res = run_scanner(["2330","2317","2454","2303","2382","3231","2603"], "權值股")
        if res: st.table(pd.DataFrame(res))
with col3:
    if st.button("🔥 啟動小資飆股偵測"):
        with st.spinner("搜尋中..."):
            res = run_scanner(PENNY_STOCKS, "小資飆股")
            if res: st.table(pd.DataFrame(res))
            else: st.warning("目前無符合條件標的。")
