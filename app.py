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

# --- 2. 聖域分析引擎 (V28.0 高度客製化) ---
def get_v28_analysis(ticker):
    try:
        ticker = ticker.strip().upper()
        is_us = any(c.isalpha() for c in ticker)
        df = pd.DataFrame()
        
        # 數據路由
        if is_us:
            df = yf.download(ticker, period="1y", interval="1d", progress=False, auto_adjust=True)
            chart_url = f"https://www.tradingview.com/symbols/{ticker}/"
        else:
            for suf in [".TW", ".TWO"]:
                tmp = yf.download(f"{ticker}{suf}", period="1y", progress=False, auto_adjust=True)
                if not tmp.empty:
                    df = tmp
                    break
            chart_url = f"https://tw.stock.yahoo.com/quote/{ticker}/chart"
        
        if df.empty or len(df) < 60: return None

        # 數據標準化
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df.index = df.index.tz_localize(None)
        
        # 三刀流指標
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['MA60'] = ta.sma(df['Close'], length=60)
        macd = ta.macd(df['Close'])
        df['MACD_H'] = macd.iloc[:, 2] if macd is not None else 0
        df = df.dropna()
        
        now = df.iloc[-1]
        p, m5, m20, m60 = float(now['Close']), float(now['MA5']), float(now['MA20']), float(now['MA60'])
        
        # 10% 獲利回收與 5% 預警點
        target_10 = p * 1.10
        warn_5 = p * 1.05
        
        score = 0
        if p > m5: score += 20
        if p > m20: score += 40
        if m20 > m60: score += 20
        if float(now['MACD_H']) > 0: score += 20

        status = "🟢強勢" if score >= 80 else ("🔴止損" if p < m20 else "🟡觀望")
        
        return {
            "ticker": ticker, "p": p, "m5": m5, "m20": m20, "m60": m60, 
            "target": target_10, "warn": warn_5, "score": score, 
            "status": status, "url": chart_url, "df": df.tail(60)
        }
    except: return None

def push_line(msg):
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {TOKEN}"}
    payload = {"to":USER_ID, "messages":[{"type":"text", "text":msg}]}
    requests.post("https://api.line.me/v2/bot/message/push", headers=headers, data=json.dumps(payload))

# --- 3. 指揮中心介面 ---
st.set_page_config(page_title="V28 聖域監控終端", layout="wide")
st.title("🛡️ 國發聖域戰略監控終端 V28.0")
st.caption("上帝權威校準：20 個自訂欄位即時監控 10% 獲利回收系統")

# [A] 自訂 20 欄位戰略監控表
st.header("📋 24H 自訂戰略監控清單 (20 欄位)")
custom_input = st.text_area("請輸入 20 個標的代碼 (用逗號分隔，例: 2330, NVDA, 00830, TSM, VOO)", 
                           "00830, 00919, 00929, 2330, NVDA, QQQM, SCHD, SMH, TSLA, TSM, VOO, 2317, 2454, PLTR, AMD").upper()

if st.button("🚀 啟動全市場即時監控 (含 10% 獲利預估)", use_container_width=True):
    tickers = [t.strip() for t in custom_input.split(",") if t.strip()][:20]
    results = []
    
    with st.spinner("正在對標印太數據鏈..."):
        for t in tickers:
            res = get_v28_analysis(t)
            if res: results.append(res)
    
    if results:
        # 建立 20 欄位專業表格
        df_display = pd.DataFrame(results)
        df_display = df_display[['ticker', 'status', 'p', 'target', 'm20', 'score']]
        df_display.columns = ['代碼', '戰略狀態', '目前市價', '10%回收價', '生命線(20MA)', '戰力評分']
        st.table(df_display)
        
        # 執行 LINE 通知
        for r in results:
            if "🟢" in r['status'] or "🔴" in r['status']:
                msg = (f"🏛️ V28 監控報報：{r['ticker']}\n狀態：{r['status']}\n"
                       f"現價：{r['p']:.2f}\n🎯 10%回收：{r['target']:.2f}\n"
                       f"🛡️ 生命線：{r['m20']:.2f}\n📊 線圖：{r['url']}")
                push_line(msg)
        st.success(f"✅ 已完成 {len(results)} 檔標的之三刀流校準與 LINE 回報。")

# [B] 原有條件不變 - 戰略按鈕區
st.markdown("---")
st.header("⚡ 原有戰略掃描 (上帝全連結版)")
c1, c2, c3, c4 = st.columns(4)
SCAN_SEEDS = {
    "上市波段": ["2330","2317","2454","2382","2603"],
    "美股強勢": ["NVDA","TSLA","PLTR","COIN","AMD"],
    "小資飆股": ["2344","2409","2618","3481","6116"],
    "上櫃飆股": ["8046","6142","3234","3163","8069"]
}

def run_scan(mode, stocks):
    found = []
    for t in stocks:
        r = get_v28_analysis(t)
        if r and "🟢" in r['status']:
            found.append(t)
            msg = (f"🏛️ V28 {mode}綠燈：{r['ticker']}\n現價：{r['p']:.2f}\n目標：{r['target']:.2f}\n📊 圖表：{r['url']}")
            push_line(msg)
    st.success(f"{mode} 掃描完成。")

with c1:
    if st.button("📈 監控上市波段"): run_scan("上市波段", SCAN_SEEDS["上市波段"])
with c2:
    if st.button("🇺🇸 監控美股強勢"): run_scan("美股強勢", SCAN_SEEDS["美股強勢"])
with c3:
    if st.button("💰 偵測小資飆股"): run_scan("小資飆股", SCAN_SEEDS["小資飆股"])
with s4 := c4:
    if st.button("🚀 偵測上櫃飆股", type="primary"): run_scan("上櫃飆股", SCAN_SEEDS["上櫃飆股"])
