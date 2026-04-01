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

# --- 2. 數據下載與分析 (對標 TradingView 指標) ---
def get_v11_data(ticker):
    try:
        is_us = any(c.isalpha() for c in ticker)
        suf = "" if is_us else (".TW" if len(ticker)<=4 else ".TWO")
        df = yf.download(f"{ticker}{suf}", period="1y", interval="1d", progress=False)
        if not is_us and df.empty: df = yf.download(f"{ticker}.TWO", period="1y", progress=False)
        if df is None or df.empty or len(df) < 60: return None
        
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df = df.astype(float)
        
        # 技術指標計算
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['MA60'] = ta.sma(df['Close'], length=60)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        macd = ta.macd(df['Close'])
        df['MACD'] = macd['MACD_12_26_9']
        
        now = df.iloc[-1]
        p, m20 = float(now['Close']), float(now['MA20'])
        
        # 國發管理人評分與紅綠燈
        score = 0
        if p > float(now['MA5']): score += 25
        if p > m20: score += 25
        if float(now['MA20']) > float(now['MA60']): score += 20
        if now['MACD'] > 0: score += 20
        if 50 < now['RSI'] < 75: score += 10
        
        light = "🟢【強勢綠燈】" if score >= 85 and p > m20 else ("🔴【止損紅燈】" if p < m20 or score < 60 else "🟡【等待黃燈】")
        url = f"https://finance.yahoo.com/quote/{ticker}" if is_us else f"https://tw.stock.yahoo.com/quote/{ticker}"
        
        return {"df": df.tail(120), "score": score, "light": light, "p": p, "m20": m20, "url": url}
    except: return None

def send_line(msg):
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {TOKEN}"}
    payload = {"to":USER_ID,"messages":[{"type":"text","text":f"🏛️ 國發 V11 戰報：\n{msg}"}]}
    try: requests.post("https://api.line.me/v2/bot/message/push", headers=headers, data=json.dumps(payload), timeout=10)
    except: pass

# --- 3. TradingView 風格繪圖引擎 ---
def draw_tradingview_style(ticker, df):
    # 建立多圖層：K線+成交量(7:3 比例) + RSI(獨立)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                       vertical_spacing=0.05, 
                       row_heights=[0.7, 0.3])

    # A. 主圖：Candlestick + MAs
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], line=dict(color='#FF9800', width=1.5), name='5MA'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='#E91E63', width=2), name='20MA(生命線)'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], line=dict(color='#2196F3', width=2), name='60MA(趨勢線)'), row=1, col=1)

    # B. 副圖：成交量 (Volume)
    colors = ['red' if df['Open'][i] > df['Close'][i] else 'green' for i in range(len(df))]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='成交量', marker_color=colors, opacity=0.5), row=2, col=1)

    # 佈局設定 (對標 TradingView 深色模式)
    fig.update_layout(
        title=f"🏛️ {ticker} 實時戰略圖 (對標 TradingView)",
        template="plotly_dark",
        height=700,
        xaxis_rangeslider_visible=False,
        hovermode='x unified'
    )
    fig.update_yaxes(title_text="價格", row=1, col=1)
    fig.update_yaxes(title_text="成交量", row=2, col=1)
    
    st.plotly_chart(fig, use_container_width=True)

# --- 4. 介面 ---
st.set_page_config(page_title="V11 TradingView 終端", layout="wide")
st.title("🛡️ 國發 V11：全域戰略追蹤終端")

# 檢診區
c_in, c_btn = st.columns([3,1])
with c_in: diag_t = st.text_input("輸入台美股代碼 (如 2330, NVDA, 8046)", "2317").upper()
with c_btn:
    st.write("<br>", unsafe_allow_html=True)
    if st.button("🩺 執行專業檢診", use_container_width=True):
        res = get_v11_data(diag_t)
        if res:
            st.subheader(f"{res['light']} {diag_t} | 評分: {res['score']}")
            draw_tradingview_style(diag_t, res['df'])
            send_line(f"{res['light']}\n標的：{diag_t}\n現價：{res['p']:.2f}\n生命線(20MA)：{res['m20']:.2f}\n📊看圖：{res['url']}")
        else: st.error("查無資料，請確認代碼。")

# 快速掃描區
st.markdown("---")
st.markdown("### 🚀 戰略模式快選")
b1, b2, b3, b4 = st.columns(4)

def run_v11_scan(stocks, mode):
    p = st.progress(0)
    for i, t in enumerate(stocks):
        r = get_v11_data(t)
        if r and "🟢" in r['light']:
            send_line(f"🚨【{mode}綠燈】{t}\n價格：{r['p']:.2f}\nMA20支撐：{r['m20']:.2f}\n📊看圖：{r['url']}")
        p.progress((i+1)/len(stocks))
        time.sleep(0.1)
    st.success(f"{mode} 掃描完畢")

with b1:
    if st.button("📈 上市波段", use_container_width=True): run_v11_scan(["2330","2317","2454","2382","2603"], "上市波段")
with b2:
    if st.button("🇺🇸 美股強勢", use_container_width=True): run_v11_scan(["NVDA","TSLA","PLTR","COIN","AMD"], "美股強勢")
with b3:
    if st.button("💰 小資飆股", use_container_width=True): run_v11_scan(["2344","2409","2618","1605","2353"], "小資飆股")
with b4:
    if st.button("💎 上櫃飆股", type="primary", use_container_width=True): run_v11_scan(["8046","6142","3234","3163","6125","5483","8064"], "上櫃飆股")
