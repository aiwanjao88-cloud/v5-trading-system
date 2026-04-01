# -*- coding: utf-8 -*-
import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import json
import time
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- 1. 核心參數 ---
TOKEN = "p0hZsq9njQwsK2QYkeTQjYYyJ87MpttosPY8E7e6HIbJns3Ii2AnYj4Z+QNaGCVrDphhuFlGKHJCnfMleQ1XlCJj2FRu2UJTYj9dAZUFIZfB4SLcVjXncnsGLrpflCwc1O3bU4OotJqW3zeslTFk8QdB04t89/1O/w1cDnyilFU="
USER_ID = "Ud25e9519467182c8b844df5260bccde5"

# --- 2. 數據下載與分析 (支援 ETF 與 自動代碼識別) ---
def get_v11_data(ticker):
    try:
        is_us = any(c.isalpha() for c in ticker)
        df = pd.DataFrame()
        
        if is_us:
            df = yf.download(ticker, period="1y", interval="1d", progress=False)
        else:
            # 優先嘗試 .TW (上市/ETF)，失敗再嘗試 .TWO (上櫃)
            df = yf.download(f"{ticker}.TW", period="1y", interval="1d", progress=False)
            if df.empty:
                df = yf.download(f"{ticker}.TWO", period="1y", interval="1d", progress=False)
        
        if df is None or df.empty or len(df) < 60: return None
        
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df = df.astype(float)
        
        # 技術指標
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['MA60'] = ta.sma(df['Close'], length=60)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        macd = ta.macd(df['Close'])
        df['MACD'] = macd['MACD_12_26_9']
        
        now = df.iloc[-1]
        p, m20 = float(now['Close']), float(now['MA20'])
        
        score = 0
        if p > float(now['MA5']): score += 25
        if p > m20: score += 25
        if float(now['MA20']) > float(now['MA60']): score += 20
        if now['MACD'] > 0: score += 20
        if 50 < now['RSI'] < 75: score += 10
        
        light = "🟢【強勢綠燈】" if score >= 85 and p > m20 else ("🔴【止損紅燈】" if p < m20 or score < 60 else "🟡【等待黃燈】")
        return {"df": df.tail(120), "score": score, "light": light, "p": p, "m20": m20}
    except: return None

def send_line(msg):
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {TOKEN}"}
    payload = {"to":USER_ID,"messages":[{"type":"text","text":f"🏛️ 國發 V11.1 戰報：\n{msg}"}]}
    try: requests.post("https://api.line.me/v2/bot/message/push", headers=headers, data=json.dumps(payload), timeout=10)
    except: pass

# --- 3. TradingView 風格繪圖 ---
def draw_chart(ticker, df):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], line=dict(color='#FF9800', width=1.5), name='5MA'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='#E91E63', width=2), name='20MA(生命)'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], line=dict(color='#2196F3', width=2), name='60MA(趨勢)'), row=1, col=1)
    colors = ['red' if df['Open'][i] > df['Close'][i] else 'green' for i in range(len(df))]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='成交量', marker_color=colors, opacity=0.5), row=2, col=1)
    fig.update_layout(title=f"🏛️ {ticker} 戰略圖", template="plotly_dark", height=700, xaxis_rangeslider_visible=False, hovermode='x unified')
    st.plotly_chart(fig, use_container_width=True)

# --- 4. 介面 ---
st.set_page_config(page_title="V11.1 ETF 兼容版", layout="wide")
st.title("🛡️ 國發 V11.1：全市場自動化終端 (含 ETF 支援)")

c_in, c_btn = st.columns([3,1])
with c_in: diag_t = st.text_input("輸入代碼 (2330, 00830, NVDA)", "00830").upper()
with c_btn:
    st.write("<br>", unsafe_allow_html=True)
    if st.button("🩺 執行專業檢診", use_container_width=True):
        res = get_v11_data(diag_t)
        if res:
            st.subheader(f"{res['light']} {diag_t} | 評分: {res['score']}")
            draw_chart(diag_t, res['df'])
            send_line(f"{res['light']}\n標的：{diag_t}\n現價：{res['p']:.2f}\n生命線(20MA)：{res['m20']:.2f}")
        else: st.error("查無資料，請確認代碼（如 00830）。")

# 快速掃描
st.markdown("---")
b1, b2, b3, b4 = st.columns(4)
def run_scan(stocks, mode):
    p = st.progress(0)
    for i, t in enumerate(stocks):
        r = get_v11_data(t)
        if r and "🟢" in r['light']:
            send_line(f"🚨【{mode}綠燈】{t}\n價格：{r['p']:.2f}\nMA20支撐：{r['m20']:.2f}")
        p.progress((i+1)/len(stocks))
        time.sleep(0.1)
    st.success("掃描完畢")

with b1:
    if st.button("📈 上市/ETF波段", use_container_width=True): run_scan(["00830","0050","2330","2454","2317"], "上市ETF")
with b2:
    if st.button("🇺🇸 美股強勢", use_container_width=True): run_scan(["NVDA","TSLA","PLTR","SOFI"], "美股")
with b3:
    if st.button("💰 小資飆股", use_container_width=True): run_scan(["2344","2409","2618","1605"], "小資")
with b4:
    if st.button("💎 上櫃飆股", type="primary", use_container_width=True): run_scan(["8046","6142","3163","6125"], "上櫃")
