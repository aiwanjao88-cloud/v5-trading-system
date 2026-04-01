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

st.set_page_config(page_title="V7.2 小資飆股偵測器", layout="wide")
st.title("📈 V7.2 國發級全域掃描器 (小資飆股優化版)")

st.sidebar.header("🛠️ 系統狀態")
st.sidebar.success("✅ LINE 授權已自動載入")
st.sidebar.markdown("---")
st.sidebar.write("💰 **小資策略設定**：")
st.sidebar.write("- 股價區間：10 ~ 50 元")
st.sidebar.write("- 門檻：評分 > 80 + 站上 5MA")

# 權值股清單
BLUE_CHIPS = ["2330","2317","2454","2303","2382","3231","2603","2881","2882"]
# 潛力小資股清單 (包含熱門銅板股、低價電子、轉機股)
PENNY_STOCKS = ["2344","2363","2409","3481","6116","2618","2610","2883","2888","1605","1608","1609","2002","2014","2323","2353","2362","2449","3035","3706","6116","1904","2641"]

# --- 4. 掃描執行邏輯 ---

def run_scanner(target_list, mode_name="一般"):
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total = len(target_list)
    for i, ticker in enumerate(target_list):
        status_text.text(f"[{mode_name}] 掃描中 ({i+1}/{total}): {ticker}")
        progress_bar.progress((i + 1) / total)
        
        data = yf.download(f"{ticker}.TW", period="8mo", progress=False)
        if data.empty: continue

        score, now = calculate_v5_score(data)
        if now is not None:
            now_price = float(now['Close'])
            ma5 = float(now['MA5'])
            ma20 = float(now['MA20'])
            
            # --- 小資飆股過濾邏輯 ---
            if mode_name == "小資飆股":
                # 過濾：價格要在 10-50 之間，且評分要更嚴格(80分)
                if not (10 <= now_price <= 50) or score < 80:
                    continue
            else:
                # 一般模式過濾
                if score < 75:
                    continue

            # 站上 5MA 才發送
            if now_price > ma5:
                chart_url = f"https://tw.stock.yahoo.com/quote/{ticker}.TW"
                results.append({"代碼": ticker, "評分": score, "現價": round(now_price, 2), "20MA": round(ma20, 2)})
                
                msg = f"🔥【小資飆股發現】\n標的：{ticker}\n評分：{score} 分 (強勢)\n價格：{now_price:.2f}\n------------------\n💡 此標的符合低單價、高動能特徵，適合 2 萬小資操作。\n⚓ 出場防線(20MA)：{ma20:.2f}\n📊 即時看圖：\n{chart_url}"
                send_line_message(msg)
        
        time.sleep(0.1)
            
    return results

# --- 5. 主程式按鈕 ---

col1, col2, col3 = st.columns(3)

with col1:
    user_input = st.text_input("自選清單", "2330,2317,2454")
    if st.button("🚀 自選掃描"):
        res = run_scanner([t.strip() for t in user_input.split(",") if t.strip()], "自選")
        if res: st.table(pd.DataFrame(res))

with col2:
    st.write("掃描大型權值股")
    if st.button("🔍 權值股掃描"):
        res = run_scanner(BLUE_CHIPS, "權值股")
        if res: st.table(pd.
