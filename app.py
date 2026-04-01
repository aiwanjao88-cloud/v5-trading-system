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

# --- 2. 核心計算與連結邏輯 ---
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
        chart = f"https://finance.yahoo.com/quote/{ticker_str}" if is_us else f"https://tw.stock.yahoo.com/quote/{ticker_str}"
        return {"score": score, "p": float(now['Close']), "m5": float(now['MA5']), "m20": float(now['MA20']), "url": chart}
    except: return None

def send_line(msg):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {TOKEN}"}
    payload = {"to":USER_ID,"messages":[{"type":"text","text":msg}]}
    try: requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
    except: pass

# --- 3. 介面設計 ---
st.set_page_config(page_title="V7.9 專業投資終端", layout="wide")

# 自定義 CSS 讓按鈕更好看
st.markdown("""
    <style>
    div.stButton > button:first-child {
        height: 3em;
        border-radius: 10px;
        border: 1px solid #000000;
        font-size: 18px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    </style>
    """, unsafe_allow_stdio=False, unsafe_allow_html=True)

st.title("🛡️ 國發級五合一戰略儀表板")
st.markdown("---")

# 個股診斷區
st.subheader("🔍 標的深度檢診")
target = st.text_input("輸入台美股代碼 (如 2330 或 NVDA)", "2317").strip().upper()

# --- 五個戰鬥按鈕 ---
st.markdown("### ⚡ 模式切換")
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    if st.button("🩺 診斷標的", use_container_width=True):
        r = get_analysis(target)
        if r:
            send_line(f"🩺【{target}診斷】\n評分:{r['score']}\n現價:{r['p']:.2f}\n止損:{r['p']*0.93:.2f}\n📊看圖:{r['url']}")
            st.success(f"{target} 診斷報告已傳送")

with c2:
    if st.button("📈 上市飆股", use_container_width=True):
        for t in ["2344","2363","2409","3481","2618","1605","2353"]:
            r = get_analysis(t)
            if r and r['score'] >= 80 and r['p'] > r['m5']:
                send_line(f"🚨【上市飆】{t}\n評分:{r['score']}\n價格:{r['p']:.2f}\n📊看圖:{r['url']}")
        st.success("上市清單掃描完畢")

with c3:
    if st.button("🇺🇸 美股偵測", use_container_width=True):
        for t in ["NVDA","TSLA","AMD","PLTR","COIN","MARA"]:
            r = get_analysis(t)
            if r and r['score'] >= 80 and r['p'] > r['m5']:
                send_line(f"🇺🇸【美飆股】{t}\n評分:{r['score']}\n價格:{r['p']:.2f}\n📊看圖:{r['url']}")
        st.success("美股清單掃描完畢")

with c4:
    if st.button("🏛️ 權值守護", use_container_width=True):
        for t in ["2330","2317","2454"]:
            r = get_analysis(t)
            if r: send_line(f"⚖️【權值報告】{t}\n評分:{r['score']}\n📊看圖:{r['url']}")
        st.success("權值大盤監控完畢")

with c5:
    # 使用 type="primary" 讓最重要的按鈕變色 (通常是鮮艷的顏色)
    if st.button("💰 櫃買飆股", type="primary", use_container_width=True):
        for t in ["8046","6142","3234","3163","4533","6125","5483","6290","8064"]:
            r = get_analysis(t)
            if r and r['score'] >= 80 and r['p'] > r['m5'] and 10 <= r['p'] <= 60:
                send_line(f"🚀【櫃買飆】{t}\n評分:{r['score']}\n現價:{r['p']:.2f}\n📊看圖:{r['url']}")
        st.success("櫃買強勢股掃描完畢")

st.markdown("---")
st.caption("系統提示：按鈕 5 鎖定櫃買低價股(10-60元)。所有模式均搭配 5MA 濾網與即時圖表。")
