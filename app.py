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

# --- 1. 機構級參數授權 ---
TOKEN = "p0hZsq9njQwsK2QYkeTQjYYyJ87MpttosPY8E7e6HIbJns3Ii2AnYj4Z+QNaGCVrDphhuFlGKHJCnfMleQ1XlCJj2FRu2UJTYj9dAZUFIZfB4SLcVjXncnsGLrpflCwc1O3bU4OotJqW3zeslTFk8QdB04t89/1O/w1cDnyilFU="
USER_ID = "Ud25e9519467182c8b844df5260bccde5"

# --- 2. 專業級數據處理引擎 (對標 Alpha Vantage 與 TradingView) ---
def get_v14_data(ticker):
    try:
        ticker = ticker.strip().upper()
        is_us = any(c.isalpha() for c in ticker)
        
        # 多源路徑識別 (對標 FMP 數據源穩定性)
        full_ticker = ticker if is_us else f"{ticker}.TW"
        tk = yf.Ticker(full_ticker)
        df = tk.history(period="1y", interval="1d", auto_adjust=True)
        
        if df.empty and not is_us:
            full_ticker = f"{ticker}.TWO"
            tk = yf.Ticker(full_ticker)
            df = tk.history(period="1y", interval="1d", auto_adjust=True)

        if df is None or df.empty or len(df) < 60: return None
        
        # 數據清洗：解決除權息偏移與 MultiIndex 問題
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df = df.astype(float)
        
        # 專業指標校準 (對標 TradingView Standard)
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['MA60'] = ta.sma(df['Close'], length=60)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        # MACD 採用機構常用的 12, 26, 9 指數移動平均
        macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
        df['MACD'] = macd['MACD_12_26_9']
        df['MACD_S'] = macd['MACDs_12_26_9']
        df['MACD_H'] = macd['MACDh_12_26_9']
        
        df = df.dropna()
        now = df.iloc[-1]
        p, m5, m20, m60 = now['Close'], now['MA5'], now['MA20'], now['MA60']
        
        # 機構級紅綠燈邏輯 (高準確度過濾)
        score = 0
        # 1. 趨勢判定 (權重 40)
        if p > m5 and p > m20: score += 40
        # 2. 均線排列 (權重 30) - 判斷多頭起飛
        if m5 > m20 and m20 > m60: score += 30
        # 3. 動能判定 (權重 30) - MACD 金叉且 RSI 位於強勢區
        if now['MACD_H'] > 0 and 50 < now['RSI'] < 75: score += 30
        
        light = "🟢【機構強勢買入】" if score >= 85 else ("🔴【防禦減碼止損】" if p < m20 or score < 50 else "🟡【區間橫盤觀望】")
        
        # 新聞摘要抓取
        news_list = tk.news[:3]
        news_text = "\n".join([f"▪️ {n['title']}" for n in news_list]) if news_list else "暫無重大新聞披露。"
        
        return {
            "df": df.tail(100), "score": score, "light": light, "p": p, 
            "m5": m5, "m20": m20, "m60": m60, "news": news_text,
            "url": f"https://www.moneydj.com/KMDJ/Search/SearchViewer.aspx?search={ticker}" if not is_us else f"https://finance.yahoo.com/quote/{ticker}"
        }
    except: return None

def send_v14_report(ticker, res):
    msg = (
        f"🏛️ 國發 V14 戰略報告：{ticker}\n"
        f"評級：{res['light']}\n"
        f"現價：{res['p']:.2f} | 分數：{res['score']}\n"
        f"------------------\n"
        f"🎯 進場(5MA)：{res['m5']:.2f}\n"
        f"🛡️ 止損(20MA)：{res['m20']:.2f}\n"
        f"📈 趨勢(60MA)：{res['m60']:.2f}\n"
        f"------------------\n"
        f"📰 重大即時情報：\n{res['news']}\n"
        f"🔗 官方情報源：{res['url']}"
    )
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {TOKEN}"}
    payload = {"to":USER_ID, "messages":[{"type":"text", "text":msg}]}
    requests.post("https://api.line.me/v2/bot/message/push", headers=headers, data=json.dumps(payload), timeout=10)

# --- 3. 介面與繪圖 (TradingView 2026 風格) ---
st.set_page_config(page_title="V14 國發機構級終端", layout="wide")
st.title("🛡️ 國發級投資終端 V14.0 (對標機構數據源)")

diag_t = st.text_input("🔍 全球標的快速檢診 (2330, 00830, NVDA)", "2317").upper()

if st.button("🚀 執行深度戰術分析", use_container_width=True):
    with st.spinner("正在對標 TradingView 與 MoneyDJ 數據庫..."):
        res = get_v14_data(diag_t)
        if res:
            st.subheader(f"{res['light']} {diag_t}")
            c1, c2 = st.columns(2)
            with c1: st.info(f"📰 **即時情報摘要：**\n{res['news']}")
            with c2: st.warning(f"⚖️ **進出評估建議：**\n進場參考：{res['m5']:.2f}\n止損防線：{res['m20']:.2f}")
            
            # 專業 K 線圖
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=res['df'].index, open=res['df']['Open'], high=res['df']['High'], low=res['df']['Low'], close=res['df']['Close'], name='K線'), row=1, col=1)
            fig.add_trace(go.Scatter(x=res['df'].index, y=res['df']['MA20'], line=dict(color='#E91E63', width=2), name='20MA'), row=1, col=1)
            fig.add_trace(go.Scatter(x=res['df'].index, y=res['df']['MA60'], line=dict(color='#2196F3', width=2), name='60MA'), row=1, col=1)
            fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
            
            send_v14_report(diag_t, res)
        else: st.error("查無資料，請確認代碼。")

# 戰略監控區域
st.markdown("---")
b1, b2, b3, b4 = st.columns(4)
def run_v14_scan(stocks, mode):
    p = st.progress(0)
    for i, t in enumerate(stocks):
        r = get_v14_data(t)
        if r and "🟢" in r['light']: send_v14_report(t, r)
        p.progress((i+1)/len(stocks))
        time.sleep(0.5)
    st.success(f"✅ {mode} 掃描完畢")

with b1:
    if st.button("📈 上市/ETF 監控", use_container_width=True): run_v14_scan(["00830","0050","00929","2330"], "波段")
with b2:
    if st.button("🇺🇸 美股強勢監控", use_container_width=True): run_v14_scan(["NVDA","TSLA","PLTR","AAPL","SOFI"], "美股")
with b3:
    if st.button("💰 小資飆股偵測", use_container_width=True): run_v14_scan(["2344","2409","2618","1605"], "小資")
with b4:
    if st.button("🚀 上櫃飆股偵測", type="primary", use_container_width=True): run_v14_scan(["8046","6142","3163","6125","5483"], "上櫃")
