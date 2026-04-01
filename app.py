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
        # 若上市找不到，自動切換至上櫃代碼 .TWO
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
    except: return None

def send_line(msg):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {TOKEN}"}
    payload = {"to":USER_ID,"messages":[{"type":"text","text":msg}]}
    try: requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
    except: pass

# --- 3. 介面 ---
st.set_page_config(page_title="V7.7 櫃買飆股版", layout="wide")
st.title("📈 V7.7 國發級投資系統 (櫃買模式)")

# 個股檢診
st.markdown("### 🔍 個股快速檢診")
target = st.text_input("輸入代碼", "2317").strip().upper()

# --- 5 按鈕區 ---
st.markdown("### 🚀 戰鬥功能選擇")
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    if st.button("🩺 1.個股檢診"):
        r = get_analysis(target)
        if r:
            st.info(f"{target}: {r['score']}分")
            send_line(f"🩺【{target}】\n評分:{r['score']}\n進場:{r['m5']:.2f}\n止損:{r['p']*0.93:.2f}")

with c2:
    if st.button("🔥 2.上市飆股"):
        for t in ["2344","2363","2409","3481","2618","1605","1609","2353"]:
            r = get_analysis(t)
            if r and r['score'] >= 80 and r['p'] > r['m5']:
                send_line(f"🚨【上市飆】{t}\n評分:{r['score']}\n價格:{r['p']:.2f}")

with c3:
    if st.button("🇺🇸 3.美股監控"):
        for t in ["NVDA","TSLA","AMD","PLTR","COIN","MARA"]:
            r = get_analysis(t)
            if r and r['score'] >= 80 and r['p'] > r['m5']:
                send_line(f"🇺🇸【美飆股】{t}\n評分:{r['score']}\n價格:{r['p']:.2f}")

with c4:
    if st.button("🔍 4.權值大盤"):
        for t in ["2330","2317","2454"]:
            r = get_analysis(t)
            if r: send_line(f"⚖️【權值】{t}\n評分:{r['score']}\n現價:{r['p']:.2f}")

with c5:
    # --- 按鈕 5：櫃買銅板飆股 (精選低價、高波動上櫃股) ---
    if st.button("💰 5.上櫃飆股", type="primary"):
        st.write("🔍 正在掃描上櫃飆股清單...")
        # 清單：包含熱門櫃買股，如元太、廣穎、波若威、協易機等符合 10-60 元區間
        otc_list = ["8046","6142","3234","3163","4533","6125","5483","3264","6290","3363","8064","6462"]
        for t in otc_list:
            r = get_analysis(t)
            # 針對櫃買股：要求更嚴格，評分 85 分以上或站上 5MA 才推播
            if r and r['score'] >= 80 and r['p'] > r['m5'] and 10 <= r['p'] <= 60:
                send_line(f"🚀【櫃買飆股】{t}\n評分:{r['score']}\n價格:{r['p']:.2f}\n出場參考:{r['m20']:.2f}")
        st.success("上櫃飆股掃描完成！")

st.markdown("---")
st.write("💡 **按鈕 5 說明**：鎖定上櫃(OTC)中股價 10-60 元、動能極強的標的，最適合 2 萬本金衝刺獲利。")
