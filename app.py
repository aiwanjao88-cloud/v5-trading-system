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
    except: return None

def send_line(msg):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {TOKEN}"}
    payload = {"to":USER_ID,"messages":[{"type":"text","text":msg}]}
    try: requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
    except: pass

# --- 3. 介面 ---
st.set_page_config(page_title="V7.6 國發級投資終端", layout="wide")
st.title("📈 V7.6 五合一國發級投資系統")

# 個股檢診
st.markdown("### 🔍 個股深度檢診")
target = st.text_input("輸入台/美股代碼 (如 2317 或 TSLA)", "2317").strip().upper()

# --- 按鈕區開始 ---
st.markdown("### 🚀 戰鬥模式切換")
row1_col1, row1_col2, row1_col3 = st.columns(3)
row2_col1, row2_col2 = st.columns(2)

# 按鈕 1: 個股深度檢診
with row1_col1:
    if st.button("🩺 按鈕 1：執行個股診斷", use_container_width=True):
        res = get_analysis(target)
        if res:
            st.success(f"{target} 診斷成功 (得分: {res['score']})")
            st.info(f"進場參考: {res['m5']:.2f} | 止損參考: {res['p']*0.93:.2f}")
            send_line(f"🩺【{target}診斷】\n評分:{res['score']}\n價格:{res['p']:.2f}\n止損:{res['p']*0.93:.2f}")
        else: st.error("查無資料")

# 按鈕 2: 小資飆股偵測
with row1_col2:
    if st.button("🔥 按鈕 2：啟動小資飆股偵測", use_container_width=True):
        for t in ["2344","2363","2409","3481","6116","2618","2610","2883","1605","1609"]:
            r = get_analysis(t)
            if r and r['score'] >= 80 and r['p'] > r['m5']:
                send_line(f"🚨【小資飆股】{t}\n評分:{r['score']}\n現價:{r['p']:.2f}")
        st.success("台股小資掃描完畢")

# 按鈕 3: 美股飆股偵測
with row1_col3:
    if st.button("🇺🇸 按鈕 3：啟動美股飆股偵測", use_container_width=True):
        for t in ["NVDA","TSLA","AAPL","AMD","PLTR","COIN","MARA","U"]:
            r = get_analysis(t)
            if r and r['score'] >= 80 and r['p'] > r['m5']:
                send_line(f"🚨【美股飆股】{t}\n評分:{r['score']}\n價格:{r['p']:.2f}")
        st.success("美股掃描完畢")

# 按鈕 4: 權值大股掃描
with row2_col1:
    if st.button("🔍 按鈕 4：權值大股守護掃描", use_container_width=True):
        for t in ["2330","2317","2454","2303","2382","3231","2603"]:
            r = get_analysis(t)
            if r and r['score'] >= 75:
                send_line(f"⚖️【權值報告】{t}\n評分:{r['score']}\n現價:{r['p']:.2f}")
        st.success("權值股監控完畢")

# 按鈕 5: 2萬翻倍自選追蹤
with row2_col2:
    if st.button("💰 按鈕 5：2萬本金自選追蹤", use_container_width=True):
        custom = ["2317", "2618", "NVDA", "TSLA"] # 你目前最想追的 4 檔
        for t in custom:
            r = get_analysis(t)
            if r:
                send_line(f"💰【本金追蹤】{t}\n評分:{r['score']}\n進場點:{r['m5']:.2f}\n生命線:{r['m20']:.2f}")
        st.success("2萬自選清單已更新至 LINE")

st.markdown("---")
st.write("💡 提示：按鈕 5 內的股票清單可以自行在程式碼第 106 行修改。")
