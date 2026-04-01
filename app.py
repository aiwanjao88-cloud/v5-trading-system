# -*- coding: utf-8 -*-
import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import json
import time
import plotly.graph_objects as go
from datetime import datetime

# --- 1. 核心參數 ---
TOKEN = "p0hZsq9njQwsK2QYkeTQjYYyJ87MpttosPY8E7e6HIbJns3Ii2AnYj4Z+QNaGCVrDphhuFlGKHJCnfMleQ1XlCJj2FRu2UJTYj9dAZUFIZfB4SLcVjXncnsGLrpflCwc1O3bU4OotJqW3zeslTFk8QdB04t89/1O/w1cDnyilFU="
USER_ID = "Ud25e9519467182c8b844df5260bccde5"

# --- 2. 數據與指標計算 ---
def get_v95_data(ticker):
    try:
        is_us = any(c.isalpha() for c in ticker)
        suf = "" if is_us else (".TW" if len(ticker)<=4 else ".TWO")
        df = yf.download(f"{ticker}{suf}", period="1y", progress=False)
        if not is_us and df.empty: df = yf.download(f"{ticker}.TWO", period="1y", progress=False)
        if df is None or df.empty or len(df) < 60: return None
        
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df = df.astype(float)
        
        # 核心指標：5MA, 20MA, 60MA
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['MA60'] = ta.sma(df['Close'], length=60)
        
        # 動能指標：MACD, RSI
        macd = ta.macd(df['Close'])
        df['MACD'] = macd['MACD_12_26_9']
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        now = df.iloc[-1]
        p, m5, m20, m60 = float(now['Close']), float(now['MA5']), float(now['MA20']), float(now['MA60'])
        
        # 紅綠燈邏輯 (國發管理人標準)
        score = 0
        if p > m5: score += 25
        if p > m20: score += 25
        if m20 > m60: score += 20 # 多頭排列加分
        if now['MACD'] > 0: score += 20
        if 50 < now['RSI'] < 70: score += 10
        
        light = "🟢【強勢起飛】" if score >= 85 and p > m20 else ("🔴【全面撤退】" if p < m20 or score < 55 else "🟡【區間盤整】")
        url = f"https://tw.stock.yahoo.com/quote/{ticker}" if not is_us else f"https://finance.yahoo.com/quote/{ticker}"
        
        return {"df": df, "score": score, "light": light, "p": p, "m5": m5, "m20": m20, "m60": m60, "url": url}
    except: return None

def send_line(msg):
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {TOKEN}"}
    payload = {"to":USER_ID,"messages":[{"type":"text","text":f"🏛️ 國發 V9.5 戰報：\n{msg}"}]}
    requests.post("https://api.line.me/v2/bot/message/push", headers=headers, data=json.dumps(payload), timeout=10)

# --- 3. K線繪圖引擎 ---
def draw_k_chart(ticker, df):
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線')])
    fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], line=dict(color='orange', width=1.5), name='5MA'))
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='magenta', width=2), name='20MA'))
    fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], line=dict(color='cyan', width=2), name='60MA'))
    fig.update_layout(title=f"{ticker} 技術面診斷 (MA5/20/60)", yaxis_title="價格", template="plotly_dark", height=500, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

# --- 4. 介面設計 ---
st.set_page_config(page_title="國發 V9.5 終極版", layout="wide")
st.title("🛡️ 國發級投資終端 V9.5 (K線技術分析版)")

# --- 頂部：個股檢診區 ---
st.markdown("### 🩺 深度個股技術檢診")
c_in, c_btn = st.columns([3,1])
with c_in: diag_t = st.text_input("輸入代碼", "2317").upper()
with c_btn:
    if st.button("🚀 執行全方位診斷", use_container_width=True):
        res = get_v95_data(diag_t)
        if res:
            st.subheader(f"{res['light']} {diag_t} 報告")
            draw_k_chart(diag_t, res['df'])
            send_line(f"{res['light']}\n標的：{diag_t}\n評分：{res['score']}\n價格：{res['p']:.2f}\n生命線(20MA)：{res['m20']:.2f}\n決策線(60MA)：{res['m60']:.2f}\n📊看圖：{res['url']}")
            st.success("診斷完成，詳細戰訊已發送至 LINE。")

# --- 下方：五大按鈕模式 ---
st.markdown("---")
st.markdown("### ⚡ 戰略掃描 (自動包含 MA20/MA60 分析)")

def run_v95_scan(stocks, mode):
    bar = st.progress(0)
    for i, t in enumerate(stocks):
        r = get_v95_data(t)
        if r and "🟢" in r['light']:
            send_line(f"🚨【{mode}綠燈訊號】\n標的：{t}\n評分：{r['score']}\n現價：{r['p']:.2f}\nMA20：{r['m20']:.2f}\n止盈：{r['p']*1.15:.2f}\n📊看圖：{r['url']}")
        bar.progress((i+1)/len(stocks))
        time.sleep(0.2)
    st.success(f"✅ {mode} 掃描任務圓滿完成。")

b1, b2, b3, b4 = st.columns(4)
with b1:
    if st.button("📈 上市波段", use_container_width=True):
        run_v95_scan(["2330","2317","2454","2382","2603"], "上市波段")
with b2:
    if st.button("🇺🇸 美股強勢", use_container_width=True):
        run_v95_scan(["NVDA","TSLA","PLTR","COIN","AMD"], "美股強勢")
with b3:
