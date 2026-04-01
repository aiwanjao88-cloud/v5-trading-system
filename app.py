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

# --- 1. 核心安全金鑰 ---
TOKEN = "p0hZsq9njQwsK2QYkeTQjYYyJ87MpttosPY8E7e6HIbJns3Ii2AnYj4Z+QNaGCVrDphhuFlGKHJCnfMleQ1XlCJj2FRu2UJTYj9dAZUFIZfB4SLcVjXncnsGLrpflCwc1O3bU4OotJqW3zeslTFk8QdB04t89/1O/w1cDnyilFU="
USER_ID = "Ud25e9519467182c8b844df5260bccde5"

# --- 2. 機構級全域數據引擎 ---
def get_v18_ultra_data(ticker):
    try:
        ticker = ticker.strip().upper()
        is_us = any(c.isalpha() for c in ticker)
        df = pd.DataFrame()
        tk = None
        
        # 多源路徑識別
        if is_us:
            tk = yf.Ticker(ticker)
            df = tk.history(period="2y", interval="1d", auto_adjust=True)
        else:
            for suffix in [".TW", ".TWO"]:
                temp_df = yf.download(f"{ticker}{suffix}", period="2y", progress=False, auto_adjust=True)
                if not temp_df.empty:
                    df = temp_df
                    tk = yf.Ticker(f"{ticker}{suffix}")
                    break

        if df.empty or len(df) < 65: return None

        # 數據標準化與校準
        df.index = df.index.tz_localize(None)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df = df.astype(float)

        # 指標計算 (5/20/60MA 三線合一)
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['MA60'] = ta.sma(df['Close'], length=60)
        macd = ta.macd(df['Close'])
        df['MACD_H'] = macd.iloc[:, 2] if macd is not None else 0
        df = df.dropna()
        
        now = df.iloc[-1]
        p, m5, m20, m60 = now['Close'], now['MA5'], now['MA20'], now['MA60']
        
        # 籌碼與情緒判斷
        vol_avg = df['Volume'].rolling(20).mean()
        vol_ratio = float(df['Volume'].iloc[-1] / vol_avg.iloc[-1]) if vol_avg.iloc[-1] > 0 else 1
        
        # 構建多源情報矩陣 (對標 2026 最新路徑)
        sources = {
            "MoneyDJ": f"https://www.moneydj.com/KMDJ/Common/ListNewNews.aspx?index=1&search={ticker}",
            "Anue": f"https://invest.cnyes.com/twstock/TWS/{ticker}/headline" if not is_us else f"https://world.cnyes.com/quote/US/{ticker}",
            "Dog": f"https://statementdog.com/analysis/{ticker}",
            "TV": f"https://www.tradingview.com/symbols/{ticker if is_us else ticker}"
        }

        score = 0
        if p > m20: score += 40
        if float(now['MACD_H']) > 0: score += 30
        if vol_ratio > 1.2: score += 20
        if m20 > m60: score += 10

        light = "🟢【三面共振-大買】" if score >= 85 and p > m5 else ("🔴【防禦警示-止損】" if p < m20 or score < 50 else "🟡【區間等待】")
        
        return {
            "df": df.tail(120), "score": score, "light": light, 
            "p": p, "m5": m5, "m20": m20, "m60": m60, "vol_r": vol_ratio,
            "sources": sources, "news": tk.news[:3] if tk.news else []
        }
    except: return None

def send_v18_line(ticker, res):
    # 抽取新聞標題 (防止 KeyError)
    news_titles = "\n".join([f"▪️ {n.get('title','新聞加載中')}" for n in res['news']])
    msg = (f"🏛️ 國發 V18.0 全域情報：{ticker}\n"
           f"等級：{res['light']}\n"
           f"現價：{res['p']:.2f} | 評分：{res['score']}\n"
           f"------------------\n"
           f"🔥 量能：{res['vol_r']:.1f}x\n"
           f"✅ 進場參考：{res['m5']:.2f}\n"
           f"❌ 止損防線：{res['m20']:.2f}\n"
           f"------------------\n"
           f"📰 重點情報：\n{news_titles}\n"
           f"------------------\n"
           f"🔗 鉅亨網：{res['sources']['Anue']}\n"
           f"🔗 財報狗：{res['sources']['Dog']}")
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {TOKEN}"}
    payload = {"to":USER_ID, "messages":[{"type":"text", "text":msg}]}
    requests.post("https://api.line.me/v2/bot/message/push", headers=headers, data=json.dumps(payload), timeout=10)

# --- 3. 介面介面 ---
st.set_page_config(page_title="V18 國發全域終端", layout="wide")
st.title("🛡️ 國發全域情報終端 V18.0 (2026 機構對標版)")

diag_t = st.text_input("🔍 輸入全球代碼 (例: 00830, 2330, NVDA, VOO, 00929)", "00830").upper().strip()

if st.button("🚀 執行三位一體情報挖掘", use_container_width=True):
    res = get_v18_ultra_data(diag_t)
    if res:
        st.subheader(f"{res['light']} {diag_t} | 分數: {res['score']}")
        
        # 1. 專業繪圖 (對標 TradingView 三線合一)
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=res['df'].index, open=res['df']['Open'], high=res['df']['High'], low=res['df']['Low'], close=res['df']['Close'], name='K線'), row=1, col=1)
        fig.add_trace(go.Scatter(x=res['df'].index, y=res['df']['MA5'], line=dict(color='orange', width=1.2), name='5MA'), row=1, col=1)
        fig.add_trace(go.Scatter(x=res['df'].index, y=res['df']['MA20'], line=dict(color='#E91E63', width=2), name='20MA'), row=1, col=1)
        fig.add_trace(go.Scatter(x=res['df'].index, y=res['df']['MA60'], line=dict(color='#2196F3', width=2), name='60MA'), row=1, col=1)
        
        colors = ['#26a69a' if res['df']['Close'].iloc[i] >= res['df']['Open'].iloc[i] else '#ef5350' for i in range(len(res['df']))]
        fig.add_trace(go.Bar(x=res['df'].index, y=res['df']['Volume'], marker_color=colors, name='成交量'), row=2, col=1)
        fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
        
        # 2. 多源情報導航區
        st.markdown("### 🏛️ 情報導航矩陣")
        c1, c2, c3, c4 = st.columns(4)
        c1.info(f"📰 [MoneyDJ 新聞]({res['sources']['MoneyDJ']})")
        c2.success(f"🔥 [鉅亨網即時快報]({res['sources']['Anue']})")
        c3.warning(f"💎 [財報狗體質分析]({res['sources']['Dog']})")
        c4.error(f"📊 [TradingView 圖表]({res['sources']['TV']})")
        
        send_v18_line(diag_t, res)
    else:
        st.error("查無數據。請檢查代碼或資料完整度。")

# 監控功能區
st.markdown("---")
st.header("⚡ 戰略綠燈自動掃描")
b1, b2, b3, b4 = st.columns(4)
def run_scan(stocks, mode):
    p = st.progress(0)
    for i, t in enumerate(stocks):
        r = get_v18_ultra_data(t)
        if r and "🟢" in r['light']: send_v18_line(t, r)
        p.progress((i+1)/len(stocks))
        time.sleep(0.5)
    st.success("任務圓滿完成")

with b1:
    if st.button("📈 上市/ETF監控", use_container_width=True): run_scan(["0050","00830","00929","2330"], "波段")
with b2:
    if st.button("🇺🇸 美股強勢監控", use_container_width=True): run_scan(["VOO","NVDA","TSLA","AAPL","PLTR"], "美股")
with b3:
    if st.button("💰 小資飆股偵測", use_container_width=True): run_scan(["2344","2409","2618","1605"], "小資")
with b4:
    if st.button("🚀 上櫃飆股偵測", type="primary", use_container_width=True): run_scan(["8046","6142","3163","6125","5483"], "上櫃")
