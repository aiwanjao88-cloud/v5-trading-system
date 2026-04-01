# -*- coding: utf-8 -*-
import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import json

# --- 1. 設定區 ---
TOKEN = "p0hZsq9njQwsK2QYkeTQjYYyJ87MpttosPY8E7e6HIbJns3Ii2AnYj4Z+QNaGCVrDphhuFlGKHJCnfMleQ1XlCJj2FRu2UJTYj9dAZUFIZfB4SLcVjXncnsGLrpflCwc1O3bU4OotJqW3zeslTFk8QdB04t89/1O/w1cDnyilFU="
USER_ID = "Ud25e9519467182c8b844df5260bccde5"

def get_analysis_v9(ticker):
    try:
        is_us = any(c.isalpha() for c in ticker)
        suf = "" if is_us else (".TW" if len(ticker)<=4 else ".TWO")
        df = yf.download(f"{ticker}{suf}", period="1y", progress=False)
        if not is_us and df.empty: df = yf.download(f"{ticker}.TWO", period="1y", progress=False)
        if df.empty or len(df) < 35: return None
        
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df = df.astype(float)
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA20'] = ta.sma(df['Close'], length=20)
        macd = ta.macd(df['Close'])
        df['MACD'] = macd['MACD_12_26_9']
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        now = df.iloc[-1]
        p, m5, m20 = float(now['Close']), float(now['MA5']), float(now['MA20'])
        
        # 評分邏輯
        score = 0
        if p > m5: score += 40
        if m5 > m20: score += 30
        if now['MACD'] > 0: score += 20
        if 50 < now['RSI'] < 70: score += 10
        
        # 紅綠燈判定
        light = "🟢強勢綠燈" if score >= 85 and p > m5 else ("🔴危險紅燈" if p < m20 or score < 60 else "🟡觀望黃燈")
        
        url = f"https://tw.stock.yahoo.com/quote/{ticker}" if not is_us else f"https://finance.yahoo.com/quote/{ticker}"
        
        report = f"{light}\n評分：{score}\n價格：{p:.2f}\n進場點：{m5:.2f}\n波段止損：{m20:.2f}\n止盈目標：{p*1.15:.2f}\n📊看圖：{url}"
        return report
    except: return None

def send_line(msg):
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {TOKEN}"}
    payload = {"to":USER_ID,"messages":[{"type":"text","text":msg}]}
    requests.post("https://api.line.me/v2/bot/message/push", headers=headers, data=json.dumps(payload), timeout=10)

# --- Streamlit UI ---
st.set_page_config(page_title="V9.0 戰略監控", layout="wide")
st.title("🛡️ V9.0 國發級全自動監控終端")

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.write("🩺 **個股健診**")
    t = st.text_input("代碼", "2317", key="t1").strip().upper()
    if st.button("執行診斷"):
        rep = get_analysis_v9(t)
        if rep: send_line(f"🩺【官方健診報告】\n標的：{t}\n{rep}"); st.success("已發送")
with c2:
    if st.button("📈 上市波段飆股", type="primary"):
        for t in ["2330","2317","2454","2382","2603"]:
            rep = get_analysis_v9(t)
            if "🟢" in str(rep): send_line(f"🚀【上市綠燈訊號】\n標的：{t}\n{rep}")
with c3:
    if st.button("🇺🇸 美股強勢訊號"):
        for t in ["NVDA","TSLA","PLTR","COIN"]:
            rep = get_analysis_v9(t)
            if "🟢" in str(rep): send_line(f"🇺🇸【美股綠燈訊號】\n標的：{t}\n{rep}")
with c4:
    if st.button("💰 小資飆股訊號"):
        for t in ["2344","2409","2618","1605"]:
            rep = get_analysis_v9(t)
            if "🟢" in str(rep): send_line(f"🔥【小資綠燈訊號】\n標的：{t}\n{rep}")
with c5:
    if st.button("🚀 上櫃飆股訊號"):
        for t in ["8046","6142","3234","3163","6125"]:
            rep = get_analysis_v9(t)
            if "🟢" in str(rep): send_line(f"💎【上櫃綠燈訊號】\n標的：{t}\n{rep}")
