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

# --- 2. 聖域分析與連結注入引擎 ---
def get_v27_analysis(ticker):
    try:
        ticker = ticker.strip().upper()
        is_us = any(c.isalpha() for c in ticker)
        df = pd.DataFrame()
        tk_obj = None

        # 多重數據路由
        if is_us:
            tk_obj = yf.Ticker(ticker)
            df = tk_obj.history(period="2y", interval="1d", auto_adjust=True)
            chart_url = f"https://www.tradingview.com/symbols/{ticker}/"
        else:
            for suf in [".TW", ".TWO"]:
                tmp = yf.download(f"{ticker}{suf}", period="2y", progress=False, auto_adjust=True)
                if not tmp.empty:
                    df, tk_obj = tmp, yf.Ticker(f"{ticker}{suf}")
                    break
            chart_url = f"https://tw.stock.yahoo.com/quote/{ticker}/chart"
        
        if df.empty or len(df) < 65: return None

        # 數據清洗
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df.index = df.index.tz_localize(None)
        df = df.astype(float)

        # 刀神三刀流指標
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['MA60'] = ta.sma(df['Close'], length=60)
        macd = ta.macd(df['Close'])
        df['MACD_H'] = macd.iloc[:, 2] if macd is not None else 0
        df = df.dropna()
        
        now = df.iloc[-1]
        p, m5, m20, m60 = float(now['Close']), float(now['MA5']), float(now['MA20']), float(now['MA60'])
        vol_avg = df['Volume'].rolling(20).mean().iloc[-1]
        vol_r = float(df['Volume'].iloc[-1] / vol_avg) if vol_avg > 0 else 1
        
        # 目標價與評分
        target_p = p * 1.08 if p > m20 else p * 1.04
        score = 0
        if p > m5: score += 20
        if p > m20: score += 40
        if m20 > m60: score += 20
        if float(now['MACD_H']) > 0: score += 10
        if vol_r > 1.2: score += 10

        status = "🟢【強勢起飛】" if score >= 85 and p > m5 else ("🔴【止損出倉】" if p < m20 else "🟡【區間整理】")
        
        return {
            "ticker": ticker, "df": df.tail(100), "score": score, "light": status, 
            "p": p, "m5": m5, "m20": m20, "m60": m60, "vol_r": vol_r, "target": target_p,
            "url": chart_url, "news": tk_obj.news[:2] if tk_obj and tk_obj.news else []
        }
    except: return None

# --- 3. 強化回報系統 (含技術連結) ---
def push_line(text):
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {TOKEN}"}
    payload = {"to":USER_ID, "messages":[{"type":"text", "text":text}]}
    requests.post("https://api.line.me/v2/bot/message/push", headers=headers, data=json.dumps(payload), timeout=10)

def send_v27_report(res, mode="戰略掃描"):
    msg = (f"🏛️ 國發 V27.0 聖域通報 - {mode}\n標的：{res['ticker']}\n等級：{res['light']}\n"
           f"------------------\n現價：{res['p']:.2f} | 評分：{res['score']}\n"
           f"🎯 預期目標：{res['target']:.2f}\n"
           f"------------------\n⚔️ 5MA：{res['m5']:.2f} | 🛡️ 20MA：{res['m20']:.2f}\n"
           f"📈 60MA：{res['m60']:.2f} | 🔥 量比：{res['vol_r']:.1f}x\n"
           f"------------------\n📊 即時技術線圖：\n{res['url']}")
    push_line(msg)

# --- 4. 指揮介面 ---
st.set_page_config(page_title="V27 聖域全連結版", layout="wide")
st.title("🛡️ 國發投資終端 V27.0 (上帝全連結版)")
st.caption("2026 印太戰略 x 刀神三刀流 | 每個回報皆附帶即時線圖連結")

# 深度分析按鈕
diag_t = st.text_input("🔍 輸入標的診斷 (00929, NVDA, 2330)", "00830").upper().strip()
if st.button("🚀 啟動聖域診斷 (附圖連結)", use_container_width=True):
    res = get_v27_analysis(diag_t)
    if res:
        st.subheader(f"{res['light']} {diag_t} | 目標: {res['target']:.2f}")
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=res['df'].index, open=res['df']['Open'], high=res['df']['High'], low=res['df']['Low'], close=res['df']['Close'], name='K線'), row=1, col=1)
        fig.add_trace(go.Scatter(x=res['df'].index, y=res['df']['MA20'], line=dict(color='#E91E63', width=2), name='20MA'), row=1, col=1)
        fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
        send_v27_report(res, "深度診斷")
    else: st.error("數據異常。")

# 戰略掃描按鈕區
st.markdown("---")
st.header("⚡ 全市場監控與回報 (含圖表連結)")
s1, s2, s3, s4 = st.columns(4)
SCAN_SEEDS = {
    "上市波段": ["2330","2317","2454","2382","2603"],
    "美股強勢": ["NVDA","TSLA","PLTR","COIN","AMD","VOO"],
    "小資飆股": ["2344","2409","2618","3481","6116"],
    "上櫃飆股": ["8046","6142","3234","3163","8069"]
}

def run_v27_mission(mode, stocks):
    st.info(f"執行 {mode} 掃描中...")
    bar = st.progress(0)
    found = []
    for i, t in enumerate(stocks):
        r = get_v27_analysis(t)
        if r and "🟢" in r['light'] and r['p'] > r['m5']:
            found.append(t)
            send_v27_report(r, mode)
        bar.progress((i+1)/len(stocks))
        time.sleep(0.3)
    summary = f"🏛️ 聖域結報：{mode}\n發現 {len(found)} 檔標的符合標準。" if found else f"🏛️ 聖域結報：{mode}\n未發現綠燈。建議現金保本。"
    push_line(summary)
    st.success(summary)

with s1:
    if st.button("📈 監控上市波段"): run_v27_mission("上市波段", SCAN_SEEDS["上市波段"])
with s2:
    if st.button("🇺🇸 監控美股強勢"): run_v27_mission("美股強勢", SCAN_SEEDS["美股強勢"])
with s3:
    if st.button("💰 偵測小資飆股"): run_v27_mission("小資飆股", SCAN_SEEDS["小資飆股"])
with s4:
    if st.button("🚀 偵測上櫃飆股", type="primary"): run_v27_mission("上櫃飆股", SCAN_SEEDS["上櫃飆股"])
