# -*- coding: utf-8 -*-
import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import json
import time

# --- 1. 固定設定區 ---
TOKEN = "p0hZsq9njQwsK2QYkeTQjYYyJ87MpttosPY8E7e6HIbJns3Ii2AnYj4Z+QNaGCVrDphhuFlGKHJCnfMleQ1XlCJj2FRu2UJTYj9dAZUFIZfB4SLcVjXncnsGLrpflCwc1O3bU4OotJqW3zeslTFk8QdB04t89/1O/w1cDnyilFU="
USER_ID = "Ud25e9519467182c8b844df5260bccde5"

# --- 2. 核心邏輯函數 ---
def calculate_score(df):
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

def send_line(msg):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {TOKEN}"}
    payload = {"to":USER_ID,"messages":[{"type":"text","text":msg}]}
    try: requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
    except: pass

# --- 3. 介面與診斷 ---
st.set_page_config(page_title="V7.5 戰鬥版", layout="wide")
st.title("📈 V7.5 國發級檢診系統")

st.header("🔍 個股進退場深度檢診")
ticker = st.text_input("輸入代碼 (如 2317 或 NVDA)", "2317").strip().upper()

if st.button("🩺 執行診斷"):
    with st.spinner("分析中..."):
        is_us = any(c.isalpha() for c in ticker)
        suf = "" if is_us else ".TW"
        df = yf.download(f"{ticker}{suf}", period="1y", progress=False)
        if not is_us and df.empty: df = yf.download(f"{ticker}.TWO", period="1y", progress=False)
        
        if not df.
