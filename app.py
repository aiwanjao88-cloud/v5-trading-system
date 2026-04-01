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

# --- 2. 核心數據引擎 (修復索引衝突) ---
def get_v12_stable_data(ticker):
    try:
        is_us = any(c.isalpha() for c in ticker)
        df = pd.DataFrame()
        if is_us:
            df = yf.download(ticker, period="1y", interval="1d", progress=False)
        else:
            df = yf.download(f"{ticker}.TW", period="1y", interval="1d", progress=False)
            if df.empty: df = yf.download(f"{ticker}.TWO", period="1y", interval="1d", progress=False)
        
        if df is None or df.empty or len(df) < 60: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df = df.astype(float)
        
        # 指標計算
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['MA60'] = ta.sma(df['Close'], length=60)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        macd = ta.macd(df['Close'])
        df['MACD'] = macd['MACD_12_26_9']
        
        # 移除含有空值的行，確保索引對齊
        df = df.dropna()
        if df.empty: return None
        
        now = df.iloc[-1]
        p = float(now['Close'])
        m5 = float(now['MA5'])
        m20 = float(now['MA20'])
        m60 = float(now['MA60'])
        
        # 評分與紅綠燈
        score = 0
        if p > m5: score += 25
        if p > m20: score += 25
        if m20 > m60: score += 20
        if now['MACD'] > 0: score += 20
        if 50 < now['RSI'] < 75: score += 10
        
        light = "🟢【建議進場】" if score >= 85 and p > m20 else ("🔴【絕對止損】" if p < m20 or score < 55 else "🟡【持有觀望】")
        mdj_url = f"https://www.moneydj.com/KMDJ/Search/SearchViewer.aspx?search={ticker}" if not is_us else f"https://finance.yahoo.com/quote/{ticker}/news"
        
        return {"df": df.tail(100), "score": score, "light": light, "p": p, "m5": m5, "m20": m20, "m60": m60, "mdj": mdj_url}
    except: return None

def send_line(msg):
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {TOKEN}"}
    payload = {"to":USER_ID,"messages":[{"type":"text","text":f"🏛️ 國發 V12.1 戰報：\n{msg}"}]}
    try: requests.post("https://api.line.me/v2/bot/message/push", headers=headers, data=json.dumps(payload), timeout=10)
    except: pass

# --- 3. 繪圖引擎 ---
def draw_stable_chart(ticker, df):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='#E91E63', width=2), name='20MA'), row=1, col=1)
    
    # 成交量顏色
    colors = ['#26a69a' if df['Close'].iloc[i] >= df['Open'].iloc[i] else '#ef5350' for i in range(len(df))]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, opacity=0.5, name='成交量'), row=2, col=1)
    
    fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False, hovermode='x unified')
    st.plotly_chart(fig, use_container_width=True)

# --- 4. 介面設計 ---
st.set_page_config(page_title="V12.1 國發穩定版", layout="wide")
st.title("🛡️ 國發 V12.1：全市場情報分析終端")

c_in, c_btn = st.columns([3,1])
with c_in: diag_t = st.text_input("輸入代碼 (2330, 00929, NVDA)", "00929").upper()
with c_btn:
    st.write("<br>", unsafe_allow_html=True)
    if st.button("🚀 執行深度檢診", use_container_width=True):
        res = get_v12_stable_data(diag_t)
        if res:
            st.subheader(f"{res['light']} {diag_t} | 評分: {res['score']}")
            
            inf1, inf2 = st.columns(2)
            with inf1:
                st.info(f"📰 **MoneyDJ 情報**\n\n[點擊查看 {diag_t} 法人報告]({res['mdj']})")
            with inf2:
                st.warning(f"⚖️ **進出場戰略**\n\n進場參考: {res['m5']:.2f} | 止損防線: {res['m20']:.2f}")

            draw_stable_chart(diag_t, res['df'])
            send_line(f"{res['light']}\n標的：{diag_t}\n評分：{res['score']}\n📰MoneyDJ情報：{res['mdj']}")
        else: st.error("查無資料或數據下載失敗。")

# 快速掃描
st.markdown("---")
st.header("⚡ 戰略監控清單")
b1, b2, b3, b4 = st.columns(4)
def run_scan(stocks, mode):
    p = st.progress(0)
    for i, t in enumerate(stocks):
        r = get_v12_stable_data(t)
        if r and "🟢" in r['light']:
            send_line(f"🚨【{mode}綠燈】{t}\n評分:{r['score']}\n現價:{r['p']:.2f}\n📊MoneyDJ:{r['mdj']}")
        p.progress((i+1)/len(stocks))
        time.sleep(0.1)
    st.success(f"{mode} 監控完畢")

with b1:
    if st.button("📈 上市/ETF監控", use_container_width=True): run_scan(["00830","0050","00929","2330","2317"], "上市ETF")
with b2:
    if st.button("🇺🇸 美股強勢監控", use_container_width=True): run_scan(["NVDA","TSLA","PLTR","AAPL"], "美股")
with b3:
    if st.button("💰 小資飆股偵測", use_container_width=True): run_scan(["2344","2409","2618","1605"], "小資")
with b4:
    if st.button("💎 上櫃飆股偵測", type="primary", use_container_width=True): run_scan(["8046","6142","3163","6125","5483"], "上櫃")
