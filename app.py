# -*- coding: utf-8 -*-
import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import json
import time

# --- 1. 固定金鑰 ---
TOKEN = "p0hZsq9njQwsK2QYkeTQjYYyJ87MpttosPY8E7e6HIbJns3Ii2AnYj4Z+QNaGCVrDphhuFlGKHJCnfMleQ1XlCJj2FRu2UJTYj9dAZUFIZfB4SLcVjXncnsGLrpflCwc1O3bU4OotJqW3zeslTFk8QdB04t89/1O/w1cDnyilFU="
USER_ID = "Ud25e9519467182c8b844df5260bccde5"

# --- 2. 核心計算邏輯 ---
def get_analysis(ticker_str):
    try:
        is_us = any(c.isalpha() for c in ticker_str)
        suf = "" if is_us else ".TW"
        df = yf.download(f"{ticker_str}{suf}", period="1y", progress=False)
        if not is_us and df.empty:
            df = yf.download(f"{ticker_str}.TWO", period="1y", progress=False)
        if df.empty or len(df) < 35: return None
        
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
        
        now = df.iloc[-1]
        score = 0
        if now['Close'] > now['EMA12']: score += 30
        if now['EMA12'] > now['EMA26']: score += 30
        if now['MACD'] > 0: score += 20
        if 50 < now['RSI'] < 70: score += 20
        
        url = f"https://finance.yahoo.com/quote/{ticker_str}" if is_us else f"https://tw.stock.yahoo.com/quote/{ticker_str}"
        return {"score": score, "p": float(now['Close']), "m5": float(now['MA5']), "m20": float(now['MA20']), "url": url}
    except:
        return None

def send_line(msg):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {TOKEN}"}
    payload = {"to":USER_ID,"messages":[{"type":"text","text":msg}]}
    try: requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
    except: pass

# --- 3. 介面設計 ---
st.set_page_config(page_title="V8.0 國發投資終端", layout="wide")
st.title("🛡️ 國發級五大戰略掃描系統")
st.markdown("---")

# 按鈕區域佈局
c1, c2, c3, c4, c5 = st.columns(5)

# --- 按鈕 1：個股檢診 ---
with c1:
    st.write("🩺 **個股診斷**")
    diag_target = st.text_input("輸入代碼", "2317", key="diag").strip().upper()
    if st.button("🔍 開始檢診", use_container_width=True):
        r = get_analysis(diag_target)
        if r:
            msg = f"🩺【個股檢診：{diag_target}】\n評分：{r['score']}\n價格：{r['p']:.2f}\n進場點：{r['m5']:.2f}\n止損參考：{r['p']*0.93:.2f}\n📊看圖：{r['url']}"
            send_line(msg)
            st.success(f"已發送 {diag_target} 報告")

# --- 按鈕 2：上市波段飆股 ---
with c2:
    st.write("📈 **上市波段**")
    if st.button("🚀 啟動掃描", key="tw_big", use_container_width=True):
        list_2 = ["2330","2317","2454","2382","3231","2603","2303","2609"]
        for t in list_2:
            r = get_analysis(t)
            if r and r['score'] >= 80:
                send_line(f"🚀【上市波段飆股】{t}\n評分：{r['score']}\n價格：{r['p']:.2f}\n📊即時看圖：{r['url']}")
        st.info("上市掃描完畢")

# --- 按鈕 3：美股強勢訊號 ---
with c3:
    st.write("🇺🇸 **美股強勢**")
    if st.button("⚡ 訊號偵測", key="us_sig", use_container_width=True):
        list_3 = ["NVDA","TSLA","AAPL","AMD","PLTR","COIN","MSFT","META"]
        for t in list_3:
            r = get_analysis(t)
            if r and r['score'] >= 85:
                send_line(f"🇺🇸【美股強勢訊號】{t}\n評分：{r['score']}\n現價：{r['p']:.2f} USD\n📊即時看圖：{r['url']}")
        st.info("美股掃描完畢")

# --- 按鈕 4：小資飆股訊號 ---
with c4:
    st.write("💰 **小資飆股**")
    if st.button("🔥 挖掘潛力", key="penny", use_container_width=True):
        list_4 = ["2344","2409","3481","6116","2618","1605","1609","2353","2324"]
        for t in list_4:
            r = get_analysis(t)
            # 鎖定低價、高動能
            if r and r['score'] >= 80 and 10 <= r['p'] <= 60:
                send_line(f"🔥【小資飆股訊號】{t}\n評分：{r['score']}\n價格：{r['p']:.2f}\n📊即時看圖：{r['url']}")
        st.info("小資掃描完畢")

# --- 按鈕 5：上櫃飆股訊號 ---
with c5:
    st.write("🚀 **上櫃飆股**")
    # type="primary" 讓按鈕變色，表示這是高爆發力的戰區
    if st.button("💎 啟動 OTC", type="primary", key="otc_sig", use_container_width=True):
        list_5 = ["8046","6142","3234","3163","4533","6125","5483","6290","8064","3363"]
        for t in list_5:
            r = get_analysis(t)
            if r and r['score'] >= 80 and r['p'] > r['m5']:
                send_line(f"💎【上櫃飆股訊號】{t}\n評分：{r['score']}\n現價：{r['p']:.2f}\n📊即時看圖：{r['url']}")
        st.info("上櫃掃描完畢")

st.markdown("---")
st.write("💡 **戰略指南**：美股每晚 9:30 開盤，上櫃股（OTC）波動最大，請務必嚴守 20MA 防線。")
