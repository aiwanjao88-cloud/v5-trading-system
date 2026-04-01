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

# --- 2. 數據下載與 MoneyDJ 連結生成 ---
def get_v12_data(ticker):
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
        
        light = "🟢【建議進場】" if score >= 85 and p > m20 else ("🔴【絕對止損】" if p < m20 or score < 60 else "🟡【持有觀望】")
        
        # MoneyDJ 連結邏輯 (台股專用)
        mdj_url = f"https://www.moneydj.com/KMDJ/Search/SearchViewer.aspx?search={ticker}" if not is_us else f"https://finance.yahoo.com/quote/{ticker}/news"
        
        return {"df": df.tail(100), "score": score, "light": light, "p": p, "m20": m20, "mdj": mdj_url}
    except: return None

def send_line(msg):
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {TOKEN}"}
    payload = {"to":USER_ID,"messages":[{"type":"text","text":f"🏛️ 國發 V12 情報：\n{msg}"}]}
    try: requests.post("https://api.line.me/v2/bot/message/push", headers=headers, data=json.dumps(payload), timeout=10)
    except: pass

# --- 3. 介面設計 ---
st.set_page_config(page_title="V12 MoneyDJ 情報版", layout="wide")
st.title("🛡️ 國發 V12：TradingView x MoneyDJ 情報終端")

# 檢診區
c_in, c_btn = st.columns([3,1])
with c_in: diag_t = st.text_input("輸入代碼 (2330, 00830, NVDA)", "2317").upper()
with c_btn:
    st.write("<br>", unsafe_allow_html=True)
    if st.button("🚀 執行深度檢診", use_container_width=True):
        res = get_v12_data(diag_t)
        if res:
            st.subheader(f"{res['light']} {diag_t} | 評分: {res['score']}")
            
            # --- 情報區域 ---
            inf1, inf2 = st.columns(2)
            with inf1:
                st.info(f"📰 **MoneyDJ 實時情報**\n\n[點擊查看 {diag_t} 法人報告與新聞]({res['mdj']})")
            with inf2:
                st.warning(f"⚖️ **戰略建議**\n\n進場參考: {float(res['df']['MA5'][-1]):.2f} | 止損: {res['m20']:.2f}")

            # 繪圖
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=res['df'].index, open=res['df']['Open'], high=res['df']['High'], low=res['df']['Low'], close=res['df']['Close'], name='K線'), row=1, col=1)
            fig.add_trace(go.Scatter(x=res['df'].index, y=res['df']['MA20'], line=dict(color='#E91E63', width=2), name='20MA'), row=1, col=1)
            fig.add_trace(go.Bar(x=res['df'].index, y=res['df']['Volume'], name='成交量', opacity=0.5), row=2, col=1)
            fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
            
            send_line(f"{res['light']}\n標的：{diag_t}\n評分：{res['score']}\n📰MoneyDJ情報：{res['mdj']}")
        else: st.error("查無資料。")

# 掃描區
st.markdown("---")
st.header("⚡ 全市場紅綠燈監控")
b1, b2, b3, b4 = st.columns(4)
def run_scan(stocks, mode):
    p = st.progress(0)
    for i, t in enumerate(stocks):
        r = get_v12_data(t)
        if r and "🟢" in r['light']:
            send_line(f"🚨【{mode}綠燈】{t}\n評分:{r['score']}\n現價:{r['p']:.2f}\n📊MoneyDJ:{r['mdj']}")
        p.progress((i+1)/len(stocks))
        time.sleep(0.1)
    st.success("監控完成")

with b1:
    if st.button("📈 上市/ETF", use_container_width=True): run_scan(["00830","2330","2454","2317","2382"], "上市")
with b2:
    if st.button("🇺🇸 美股強勢", use_container_width=True): run_scan(["NVDA","TSLA","PLTR","AAPL"], "美股")
with b3:
    if st.button("💰 小資飆股", use_container_width=True): run_scan(["2344","2409","2618","1605"], "小資")
with b4:
    if st.button("💎 上櫃飆股", type="primary", use_container_width=True): run_scan(["8046","6142","3163","6125","5483"], "上櫃")
