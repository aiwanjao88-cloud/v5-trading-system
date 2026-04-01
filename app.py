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
        df['MA60'] = ta.sma(df['Close'], length=60) # 季線
        
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
    except: pass

# --- 3. 介面設計 ---

st.set_page_config(page_title="V7.5 個股進退場檢診", layout="wide")
st.title("📈 V7.5 國發級個股檢診 (台美通用)")

# --- 4. 個股深度檢診區 ---
st.markdown("---")
st.header("🔍 個股深度檢診 (進退場建議)")
diag_ticker = st.text_input("輸入要診斷的股票代碼 (例: 2317 或 TSLA)", "2317")

if st.button("🩺 開始個股檢診"):
    with st.spinner("正在分析技術面細節..."):
        # 判斷台美股
        suffix = "" if any(c.isalpha() for c in diag_ticker) else ".TW"
        data = yf.download(f"{diag_ticker}{suffix}", period="1y", progress=False)
        if data.empty and suffix == ".TW":
            data = yf.download(f"{diag_ticker}.TWO", period="1y", progress=False)
        
        if not data.empty:
            score, now = calculate_v5_score(data)
            now_price = float(now['Close'])
            ma5 = float(now['MA5'])
            ma20 = float(now['MA20'])
            ma60 = float(now['MA60'])
            
            # --- 診斷邏輯 ---
            is_strong = now_price > ma5
            trend = "多頭排列" if ma5 > ma20 > ma60 else "盤整或轉弱"
            
            st.subheader(f"📊 {diag_ticker} 診斷報告 (現價: {now_price:.2f})")
            
            c1, c2, c3 = st.columns(3)
            c1.metric("綜合評分", f"{score} 分")
            c2.metric("5MA 位置", f"{ma5:.2f}", f"{now_price-ma5:.2f}", delta_color="normal")
            c3.metric("波段生命線", f"{ma20:.2f}")

            # --- 具體建議區 ---
            st.info(f"🚩 **趨勢判讀**：目前處於 **{trend}**。")
            
            adv_col1, adv_col2 = st.columns(2)
            with adv_col1:
                st.success("🟢 進場點建議")
                if score >= 75 and is_strong:
                    st.write(f"1. **即刻關注**：目前已站在 5MA 以上，動能強勁。")
                    st.write(f"2. **理想買點**：若回測 {ma5:.2f} 不破可分批佈局。")
                else:
                    st.write(f"1. **等待轉強**：目前評分不足或低於 5MA，建議等股價站穩 {ma5:.2f} 再進場。")

            with adv_col2:
                st.error("🔴 退場/止損建議")
                st.write(f"1. **短線止損**：跌破 {now_price*0.93:.2f} (約 7%) 強制出場。")
                st.write(f"2. **波段出場**：收盤價有效跌破 20MA ({ma20:.2f}) 獲利了結。")
            
            # 發送 LINE 深度報告
            line_msg = f"🩺【個股檢診報告：{diag_ticker}】\n評分：{score}分\n現價：{now_price:.2f}\n------------------\n✅ 進場：站穩 {ma5:.2f} 為強勢起漲點。\n❌ 止損：{now_price*0.93:.2f}\n📉 出場：跌破 20MA ({ma20:.2f})\n
