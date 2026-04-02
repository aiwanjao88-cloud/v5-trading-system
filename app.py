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

# --- 2. 聖域核心分析引擎 (V30.0) ---
def get_v30_engine(ticker):
    try:
        ticker = ticker.strip().upper()
        is_us = any(c.isalpha() for c in ticker)
        df = pd.DataFrame()
        tk_obj = None

        # 數據路由與線圖連結生成
        if is_us:
            tk_obj = yf.Ticker(ticker)
            df = tk_obj.history(period="1y", auto_adjust=True)
            chart_url = f"https://www.tradingview.com/symbols/{ticker}/"
        else:
            for suf in [".TW", ".TWO"]:
                tmp = yf.download(f"{ticker}{suf}", period="1y", progress=False, auto_adjust=True)
                if not tmp.empty:
                    df, tk_obj = tmp, yf.Ticker(f"{ticker}{suf}")
                    break
            chart_url = f"https://tw.stock.yahoo.com/quote/{ticker}/chart"
        
        if df.empty or len(df) < 60: return None

        # 數據清洗 (處理時區與索引)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df.index = df.index.tz_localize(None)
        
        # 刀神三刀流：5MA(攻擊), 20MA(生命), 60MA(趨勢)
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['MA60'] = ta.sma(df['Close'], length=60)
        macd = ta.macd(df['Close'])
        df['MACD_H'] = macd.iloc[:, 2] if macd is not None else 0
        df = df.dropna()
        
        now = df.iloc[-1]
        p, m5, m20, m60 = float(now['Close']), float(now['MA5']), float(now['MA20']), float(now['MA60'])
        
        # 10% 獲利回收點 (外資停利邏輯)
        target_10 = p * 1.10
        
        # 戰略評分系統
        score = 0
        if p > m5: score += 20
        if p > m20: score += 40
        if m20 > m60: score += 20
        if float(now['MACD_H']) > 0: score += 20

        status = "🟢強勢" if score >= 85 and p > m5 else ("🔴止損" if p < m20 else "🟡觀望")
        
        return {
            "ticker": ticker, "p": p, "m5": m5, "m20": m20, "m60": m60, 
            "target": target_10, "status": status, "url": chart_url, "score": score,
            "df": df.tail(100)
        }
    except: return None

def push_v30_line(text):
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {TOKEN}"}
    payload = {"to":USER_ID, "messages":[{"type":"text", "text":text}]}
    try: requests.post("https://api.line.me/v2/bot/message/push", headers=headers, data=json.dumps(payload), timeout=10)
    except: pass

# --- 3. 聖域 UI 介面 ---
st.set_page_config(page_title="V30 聖域矩陣終極版", layout="wide")
st.title("🛡️ 國發聖域終端 V30.0 (矩陣優化版)")

# [A] 閃電個股深度診斷
st.header("⚡ 閃電個股深度診斷")
c_in, c_btn = st.columns([4, 1])
with c_in:
    quick_ticker = st.text_input("輸入代碼 (例: 00830, NVDA, 2330)", "2317").upper().strip()
with c_btn:
    st.write("<br>", unsafe_allow_html=True)
    if st.button("🚀 執行閃電診斷", use_container_width=True):
        res = get_v30_engine(quick_ticker)
        if res:
            st.subheader(f"{res['status']} {res['ticker']} | 分數: {res['score']}")
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=res['df'].index, open=res['df']['Open'], high=res['df']['High'], low=res['df']['Low'], close=res['df']['Close'], name='K線'), row=1, col=1)
            fig.add_trace(go.Scatter(x=res['df'].index, y=res['df']['MA5'], line=dict(color='orange', width=1.5), name='5MA'), row=1, col=1)
            fig.add_trace(go.Scatter(x=res['df'].index, y=res['df']['MA20'], line=dict(color='#E91E63', width=2), name='20MA'), row=1, col=1)
            fig.add_trace(go.Scatter(x=res['df'].index, y=res['df']['MA60'], line=dict(color='#2196F3', width=2), name='60MA'), row=1, col=1)
            fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
            
            # LINE 推播
            push_v30_line(f"🏛️ V30 閃電診斷：{res['ticker']}\n狀態：{res['status']}\n現價：{res['p']:.2f}\n🎯 10%回收：{res['target']:.2f}\n📊 線圖連結：{res['url']}")
        else: st.error("查無數據，請確認代碼。")

# [B] 20 欄位自訂戰略監控矩陣
st.markdown("---")
st.header("📋 20 欄位自訂戰略監控矩陣")
custom_list = st.text_area("輸入欲追蹤之標的 (最多20個，用逗號隔開)", 
                          "00830, 00919, 00929, 2330, NVDA, QQQM, SCHD, SMH, TSLA, TSM, VOO, PLTR, AMD").upper()

if st.button("🛰️ 啟動全方位矩陣監控", type="primary", use_container_width=True):
    tickers = [t.strip() for t in custom_list.split(",") if t.strip()][:20]
    final_data = []
    bar = st.progress(0)
    for i, t in enumerate(tickers):
        r = get_v30_engine(t)
        if r:
            final_data.append(r)
        bar.progress((i + 1) / len(tickers))
    
    if final_data:
        # 顯示專業報表
        df_view = pd.DataFrame(final_data)[['ticker', 'status', 'p', 'target', 'm20', 'm60', 'score']]
        df_view.columns = ['代碼', '狀態', '現價', '10%回收價', '20MA生命', '60MA趨勢', '評分']
        st.dataframe(df_view.style.highlight_max(axis=0, subset=['評分'], color='#1e4620'), use_container_width=True)
        
        # 強制回報綠燈/紅燈至 LINE
        for r in final_data:
            if "🟢" in r['status'] or "🔴" in r['status']:
                push_v30_line(f"🦅 V30 矩陣警報：{r['ticker']}\n狀態：{r['status']}\n現價：{r['p']:.2f}\n🎯 目標：{r['target']:.2f}\n📊 圖表：{r['url']}")
        st.success("✅ 矩陣掃描完成，關鍵訊號已同步至 LINE。")

# [C] 原有戰略掃描 (一鍵執行)
st.markdown("---")
st.header("🏹 常規市場掃描")
c1, c2, c3, c4 = st.columns(4)
SCAN_SEEDS = {
    "上市": ["2330","2317","2454","2382","2603"],
    "美股": ["NVDA","TSLA","PLTR","COIN","AMD"],
    "小資": ["2344","2409","2618","3481","6116"],
    "上櫃": ["8046","6142","3234","3163","8069"]
}

def quick_scan(mode, stocks):
    st.info(f"執行 {mode} 掃描...")
    for t in stocks:
        r = get_v30_engine(t)
        if r and "🟢" in r['status']:
            push_v30_line(f"🏛️ V30 {mode}綠燈標的：{r['ticker']}\n現價：{r['p']:.2f}\n目標：{r['target']:.2f}\n📊 線圖連結：{r['url']}")
    st.success(f"{mode} 掃描完畢。")

with c1:
    if st.button("📈 監控上市波段"): quick_scan("上市", SCAN_SEEDS["上市"])
with c2:
    if st.button("🇺🇸 監控美股強勢"): quick_scan("美股", SCAN_SEEDS["美股"])
with c3:
    if st.button("💰 偵測小資飆股"): quick_scan("小資", SCAN_SEEDS["小資"])
with c4:
    if st.button("🚀 偵測上櫃飆股", type="primary"): quick_scan("上櫃", SCAN_SEEDS["上櫃"])
