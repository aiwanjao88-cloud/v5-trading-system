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
        
        return {"score": score, "p": float(now['Close']), "m5": float(now['MA5']), "m20": float(now['MA20'])}
    except:
        return None

def send_line(msg):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {TOKEN}"}
    payload = {"to":USER_ID,"messages":[{"type":"text","text":msg}]}
    try: requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
    except: pass

# --- 3. 介面 ---
st.set_page_config(page_title="V7.5 終極版", layout="wide")
st.title("📈 V7.5 國發級投資系統")

# 個股檢診
st.header("🔍 個股深度檢診")
target = st.text_input("輸入代碼 (2317 或 TSLA)", "2317").strip().upper()

if st.button("🩺 執行診斷"):
    res = get_analysis(target)
    if res:
        st.subheader(f"📊 {target} 報告 (現價: {res['p']:.2f})")
        c1, c2, c3 = st.columns(3)
        c1.metric("綜合評分", f"{res['score']}分")
        c2.metric("5MA支撐", f"{res['m5']:.2f}")
        c3.metric("20MA生命線", f"{res['m20']:.2f}")
        
        # 建議與 LINE
        st.info(f"🟢進場建議：站穩 {res['m5']:.2f}。 🔴止損參考：{res['p']*0.93:.2f}。")
        report = f"🩺【{target}檢診】\n評分:{res['score']}\n現價:{res['p']:.2f}\n進場參考:{res['m5']:.2f}\n止損參考:{res['p']*0.93:.2f}\n出場參考:{res['m20']:.2f}"
        send_line(report)
        st.success("報告已同步發送至 LINE")
    else:
        st.error("查無資料，請確認代碼。")

# 批次掃描
st.markdown("---")
st.header("🚀 策略自動監控")
col_tw, col_us = st.columns(2)

with col_tw:
    if st.button("🔥 啟動小資飆股偵測"):
        for t in ["2344","2363","2409","3481","6116","2618","2610","2883","1605","1609"]:
            r = get_analysis(t)
            if r and r['score'] >= 80 and r['p'] > r['m5']:
                send_line(f"🚨【飆股】{t}\n評分:{r['score']}\n價格:{r['p']:.2f}")
        st.success("台股掃描完成！")

with col_us:
    if st.button("🇺🇸 啟動美股飆股偵測"):
        for t in ["NVDA","TSLA","AAPL","AMD","PLTR","COIN"]:
            r = get_analysis(t)
            if r and r['score'] >= 80 and r['p'] > r['m5']:
                send_line(f"🚨【美股】{t}\n評分:{r['score']}\n價格:{r['p']:.2f}")
        st.success("美股掃描完成！")
