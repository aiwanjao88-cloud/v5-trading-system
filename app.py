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

# --- 1. 核心安全參數 ---
TOKEN = "p0hZsq9njQwsK2QYkeTQjYYyJ87MpttosPY8E7e6HIbJns3Ii2AnYj4Z+QNaGCVrDphhuFlGKHJCnfMleQ1XlCJj2FRu2UJTYj9dAZUFIZfB4SLcVjXncnsGLrpflCwc1O3bU4OotJqW3zeslTFk8QdB04t89/1O/w1cDnyilFU="
USER_ID = "Ud25e9519467182c8b844df5260bccde5"

# --- 2. 軍規級分析引擎 (修復深度分析按鈕邏輯) ---
def get_v195_analysis(ticker):
    try:
        ticker = ticker.strip().upper()
        # 判定路徑：美股不加後綴，台股需判定 .TW 或 .TWO
        is_us = any(c.isalpha() for c in ticker)
        df = pd.DataFrame()
        tk = None
        
        if is_us:
            tk = yf.Ticker(ticker)
            df = tk.history(period="1y", interval="1d", auto_adjust=True)
        else:
            for suf in [".TW", ".TWO"]:
                temp_df = yf.download(f"{ticker}{suf}", period="1y", progress=False, auto_adjust=True)
                if not temp_df.empty:
                    df = temp_df
                    tk = yf.Ticker(f"{ticker}{suf}")
                    break
        
        if df.empty or len(df) < 60: return None
        
        # 數據標準化
        df.index = df.index.tz_localize(None)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df = df.astype(float)

        # 指標計算
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['MA60'] = ta.sma(df['Close'], length=60)
        macd = ta.macd(df['Close'])
        df['MACD_H'] = macd.iloc[:, 2] if macd is not None else 0
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        df_clean = df.dropna()
        if df_clean.empty: return None
        now = df_clean.iloc[-1]
        
        # 籌碼與三維評分
        vol_avg = df['Volume'].rolling(20).mean()
        vol_ratio = float(df['Volume'].iloc[-1] / vol_avg.iloc[-1]) if vol_avg.iloc[-1] > 0 else 1
        
        score = 0
        p, m20 = now['Close'], now['MA20']
        if p > now['MA5']: score += 20
        if p > m20: score += 30
        if float(now['MACD_H']) > 0: score += 30
        if vol_ratio > 1.2: score += 20
        
        light = "🟢【建議進場】" if score >= 85 and p > now['MA5'] else ("🔴【絕對止損】" if p < m20 or score < 50 else "🟡【區間整理】")
        
        return {
            "df": df_clean.tail(120), "score": score, "light": light, 
            "p": p, "m5": now['MA5'], "m20": m20, "m60": now['MA60'], "vol_r": vol_ratio,
            "news": tk.news[:2] if tk.news else []
        }
    except: return None

def send_v195_line(ticker, res):
    msg = (f"🏛️ 國發 V19.5 戰報：{ticker}\n級別：{res['light']}\n"
           f"現價：{res['p']:.2f} | 評分：{res['score']}\n"
           f"------------------\n"
           f"✅ 進場參考：{res['m5']:.2f}\n"
           f"❌ 止損防線：{res['m20']:.2f}\n"
           f"📈 決策底線：{res['m60']:.2f}\n"
           f"🔥 量能比：{res['vol_r']:.1f}x\n"
           f"------------------\n"
           f"🔗 實時看圖：https://tw.stock.yahoo.com/quote/{ticker}")
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {TOKEN}"}
    payload = {"to":USER_ID, "messages":[{"type":"text", "text":msg}]}
    requests.post("https://api.line.me/v2/bot/message/push", headers=headers, data=json.dumps(payload))

# --- 3. 介面介面 ---
st.set_page_config(page_title="V19.5 修復版", layout="wide")
st.title("🛡️ 國發投資終端 V19.5 (深度修復加固版)")

# 診斷區
st.markdown("### 🔍 標的深度診斷")
c_in, c_btn = st.columns([3,1])
with c_in: diag_t = st.text_input("輸入代碼 (例: 2330, NVDA, 00830)", "2317").upper().strip()
with c_btn:
    st.write("<br>", unsafe_allow_html=True)
    if st.button("🚀 啟動深度分析", use_container_width=True):
        with st.spinner("數據同步與繪圖中..."):
            res = get_v195_analysis(diag_t)
            if res:
                st.subheader(f"{res['light']} {diag_t} | 評分: {res['score']}")
                # 專業 K 線圖 (對標 TradingView)
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
                fig.add_trace(go.Candlestick(x=res['df'].index, open=res['df']['Open'], high=res['df']['High'], low=res['df']['Low'], close=res['df']['Close'], name='K線'), row=1, col=1)
                fig.add_trace(go.Scatter(x=res['df'].index, y=res['df']['MA5'], line=dict(color='orange', width=1), name='5MA'), row=1, col=1)
                fig.add_trace(go.Scatter(x=res['df'].index, y=res['df']['MA20'], line=dict(color='#E91E63', width=2), name='20MA'), row=1, col=1)
                fig.add_trace(go.Scatter(x=res['df'].index, y=res['df']['MA60'], line=dict(color='#2196F3', width=2), name='60MA'), row=1, col=1)
                fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
                send_v195_line(diag_t, res)
            else:
                st.error("查無資料。請確認代碼格式（如台股 2317，美股 NVDA）。")

# 自動掃描區
st.markdown("---")
st.header("⚡ 戰略綠燈自動掃描")
b1, b2, b3, b4 = st.columns(4)
def run_scan(stocks, mode):
    p = st.progress(0)
    for i, t in enumerate(stocks):
        r = get_v195_analysis(t)
        if r and "🟢" in r['light']: send_v195_line(t, r)
        p.progress((i+1)/len(stocks))
        time.sleep(0.5)
    st.success(f"{mode} 監控完畢")

with b1:
    if st.button("📈 上市/ETF監控", use_container_width=True): run_scan(["0050","00830","00929","2330","2317","2454"], "上市")
with b2:
    if st.button("🇺🇸 美股強勢監控", use_container_width=True): run_scan(["VOO","NVDA","TSLA","AAPL","PLTR","AMD"], "美股")
with b3:
    if st.button("💰 小資飆股偵測", use_container_width=True): run_scan(["2344","2409","2618","1605","3481","6116"], "小資")
with b4:
    if st.button("🚀 上櫃飆股偵測", type="primary", use_container_width=True): run_scan(["8046","6142","3163","6125","5483","8069"], "上櫃")
