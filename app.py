# -*- coding: utf-8 -*-
# 管理人聲明：此版本已針對數據容錯與動畫流暢度完成封裝
import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import json
import time

# --- 核心參數授權 ---
TOKEN = "p0hZsq9njQwsK2QYkeTQjYYyJ87MpttosPY8E7e6HIbJns3Ii2AnYj4Z+QNaGCVrDphhuFlGKHJCnfMleQ1XlCJj2FRu2UJTYj9dAZUFIZfB4SLcVjXncnsGLrpflCwc1O3bU4OotJqW3zeslTFk8QdB04t89/1O/w1cDnyilFU="
USER_ID = "Ud25e9519467182c8b844df5260bccde5"

def get_market_analysis(ticker):
    try:
        is_us = any(c.isalpha() for c in ticker)
        suf = "" if is_us else (".TW" if len(ticker)<=4 else ".TWO")
        # 增加 retry 機制提升穩定性
        df = yf.download(f"{ticker}{suf}", period="1y", progress=False, interval="1d")
        if not is_us and df.empty: df = yf.download(f"{ticker}.TWO", period="1y", progress=False)
        
        if df is None or df.empty or len(df) < 35: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df = df.astype(float)
        
        # 技術指標計算
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA20'] = ta.sma(df['Close'], length=20)
        macd = ta.macd(df['Close'])
        df['MACD'] = macd['MACD_12_26_9']
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        now = df.iloc[-1]
        p, m5, m20 = float(now['Close']), float(now['MA5']), float(now['MA20'])
        
        # 國發評分邏輯 (加權)
        score = 0
        if p > m5: score += 40
        if m5 > m20: score += 30
        if now['MACD'] > 0: score += 20
        if 50 < now['RSI'] < 70: score += 10
        
        light = "🟢【建議進場】" if score >= 85 and p > m5 else ("🔴【絕對止損】" if p < m20 or score < 60 else "🟡【持有觀望】")
        url = f"https://tw.stock.yahoo.com/quote/{ticker}" if not is_us else f"https://finance.yahoo.com/quote/{ticker}"
        
        return f"{light}\n標的：{ticker}\n當前評分：{score}\n當前市價：{p:.2f}\n戰略支撐：{m5:.2f}\n生命防線：{m20:.2f}\n目標止盈：{p*1.2:.2f}\n📊即時線圖：{url}"
    except: return None

def send_official_report(msg):
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {TOKEN}"}
    payload = {"to":USER_ID,"messages":[{"type":"text","text":f"🏛️ 國發基金戰略報告：\n{msg}"}]}
    requests.post("https://api.line.me/v2/bot/message/push", headers=headers, data=json.dumps(payload), timeout=10)

# --- 介面渲染 ---
st.set_page_config(page_title="國發基金戰略終端", layout="wide")
st.markdown("<style>.coin-jump { font-size: 40px; text-align: center; animation: jump 1s infinite; } @keyframes jump { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-20px); } }</style>", unsafe_allow_html=True)
st.title("🏛️ 國發級戰略投資終端 V9.2")

# 管理人建議區
with st.sidebar:
    st.header("📊 管理人戰略週報")
    st.info("本週重心：關注上櫃半導體設備與美股 AI 基礎設施。2 萬元資本建議分 2 筆操作。")
    st.warning("嚴禁在 🔴 紅燈狀態下加碼攤平。")

# 五大按鈕模組
def execute_strategy(stock_list, mode):
    bar = st.progress(0)
    coin = st.empty()
    for i, t in enumerate(stock_list):
        coin.markdown(f"<div class='coin-jump'>💰</div><p style='text-align:center'>正在計算 {t} 的獲利概率...</p>", unsafe_allow_html=True)
        res = get_market_analysis(t)
        if res and "🟢" in res: send_official_report(res)
        bar.progress((i+1)/len(stock_list))
        time.sleep(0.2)
    coin.empty()
    st.success(f"✅ {mode} 掃描任務圓滿完成。")

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    diag = st.text_input("個股檢診", "2330").upper()
    if st.button("🩺 執行檢診", use_container_width=True):
        r = get_market_analysis(diag)
        if r: send_official_report(r); st.success("報告已送達")
with c2:
    if st.button("📈 上市波段", use_container_width=True):
        execute_strategy(["2330","2317","2454","2382","2603"], "上市波段")
with c3:
    if st.button("🇺🇸 美股強勢", use_container_width=True):
        execute_strategy(["NVDA","TSLA","PLTR","COIN","AMD"], "美股強勢")
with c4:
    if st.button("💰 小資飆股", use_container_width=True):
        execute_strategy(["2344","2409","2618","1605","1609"], "小資飆股")
with c5:
    if st.button("🚀 上櫃飆股", type="primary", use_container_width=True):
        execute_strategy(["8046","6142","3234","3163","6125","5483","8064"], "上櫃飆股")
