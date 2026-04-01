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

# --- 2. 專業級數據處理引擎 (V14.1 美股強化修正) ---
def get_v14_data(ticker):
    try:
        ticker = ticker.strip().upper()
        # 判定是否為美股 (含字母即判定為美股或ETF)
        is_us = any(c.isalpha() for c in ticker)
        
        # 針對美股與台股分別優化下載邏輯
        if is_us:
            # 美股直接抓取 (不加後綴)
            tk = yf.Ticker(ticker)
            df = tk.history(period="1y", interval="1d", auto_adjust=True)
        else:
            # 台股自動嘗試上市/上櫃
            df = yf.download(f"{ticker}.TW", period="1y", interval="1d", progress=False, auto_adjust=True)
            if df.empty:
                df = yf.download(f"{ticker}.TWO", period="1y", interval="1d", progress=False, auto_adjust=True)
            tk = yf.Ticker(f"{ticker}.TW" if not df.empty else f"{ticker}.TWO")

        if df is None or df.empty or len(df) < 60:
            return None
        
        # [關鍵修正] 移除時區資訊，避免指標計算報錯
        df.index = df.index.tz_localize(None)
        
        # [關鍵修正] 強制簡化欄位名稱，移除 MultiIndex
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.astype(float)
        
        # 技術指標校準
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['MA60'] = ta.sma(df['Close'], length=60)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        macd = ta.macd(df['Close'], fast=12, slow=26, signal=9)
        df['MACD_H'] = macd['MACDh_12_26_9']
        
        df = df.dropna()
        now = df.iloc[-1]
        p, m5, m20, m60 = now['Close'], now['MA5'], now['MA20'], now['MA60']
        
        # 機構評分邏輯
        score = 0
        if p > m5 and p > m20: score += 40
        if m5 > m20 > m60: score += 30
        if now['MACD_H'] > 0 and 50 < now['RSI'] < 75: score += 30
        
        light = "🟢【機構強勢買入】" if score >= 85 else ("🔴【防禦減碼止損】" if p < m20 or score < 50 else "🟡【區間橫盤觀望】")
        
        # 獲取新聞
        try:
            news_list = tk.news[:3]
            news_text = "\n".join([f"▪️ {n['title']}" for n in news_list])
        except:
            news_text = "新聞暫時無法載入。"

        return {
            "df": df.tail(100), "score": score, "light": light, "p": p, 
            "m5": m5, "m20": m20, "m60": m60, "news": news_text,
            "url": f"https://finance.yahoo.com/quote/{ticker}" if is_us else f"https://tw.stock.yahoo.com/quote/{ticker}"
        }
    except Exception as e:
        return None

def send_v14_line(ticker, res):
    msg = (f"🏛️ 國發 V14.1 戰報：{ticker}\n評級：{res['light']}\n現價：{res['p']:.2f}\n"
           f"------------------\n🎯 進場:{res['m5']:.2f}\n🛡️ 止損:{res['m20']:.2f}\n"
           f"📈 趨勢:{res['m60']:.2f}\n------------------\n"
           f"📰 即時新聞：\n{res['news']}\n🔗 數據源：{res['url']}")
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {TOKEN}"}
    payload = {"to":USER_ID, "messages":[{"type":"text", "text":msg}]}
    requests.post("https://api.line.me/v2/bot/message/push", headers=headers, data=json.dumps(payload), timeout=10)

# --- 3. 介面設計 ---
st.set_page_config(page_title="V14.1 美股強化版", layout="wide")
st.title("🛡️ 國發級投資終端 V14.1 (美股連動修復版)")

diag_t = st.text_input("🔍 全球標的診斷 (例: NVDA, TSLA, 2330)", "NVDA").upper()

if st.button("🚀 執行深度戰術分析", use_container_width=True):
    res = get_v14_data(diag_t)
    if res:
        st.subheader(f"{res['light']} {diag_t}")
        # 專業 K 線圖
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=res['df'].index, open=res['df']['Open'], high=res['df']['High'], low=res['df']['Low'], close=res['df']['Close'], name='K線'), row=1, col=1)
        fig.add_trace(go.Scatter(x=res['df'].index, y=res['df']['MA20'], line=dict(color='#E91E63', width=2), name='20MA'), row=1, col=1)
        fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
        send_v14_line(diag_t, res)
    else: st.error("查無資料。美股請確認代碼無誤（例: TSLA），台股請輸入代碼（例: 2330）。")

# 快速掃描區域
st.markdown("---")
b1, b2, b3, b4 = st.columns(4)
def run_scan(stocks, mode):
    p = st.progress(0)
    for i, t in enumerate(stocks):
        r = get_v14_data(t)
        if r and "🟢" in r['light']: send_v14_line(t, r)
        p.progress((i+1)/len(stocks))
        time.sleep(0.5)
    st.success(f"{mode} 掃描完畢")

with b1:
    if st.button("📈 上市/ETF監控", use_container_width=True): run_scan(["00830","0050","2330","2454"], "上市")
with b2:
    if st.button("🇺🇸 美股強勢監控", use_container_width=True): run_scan(["NVDA","TSLA","PLTR","AAPL","AMD"], "美股")
with b3:
    if st.button("💰 小資飆股偵測", use_container_width=True): run_scan(["2344","2409","2618","1605"], "小資")
with b4:
    if st.button("💎 上櫃飆股偵測", type="primary", use_container_width=True): run_scan(["8046","6142","3163","6125","5483"], "上櫃")
