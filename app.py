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

# --- 1. 核心安全金鑰 (聖域防線) ---
TOKEN = "p0hZsq9njQwsK2QYkeTQjYYyJ87MpttosPY8E7e6HIbJns3Ii2AnYj4Z+QNaGCVrDphhuFlGKHJCnfMleQ1XlCJj2FRu2UJTYj9dAZUFIZfB4SLcVjXncnsGLrpflCwc1O3bU4OotJqW3zeslTFk8QdB04t89/1O/w1cDnyilFU="
USER_ID = "Ud25e9519467182c8b844df5260bccde5"

# --- 2. 印太戰略分析引擎 (刀神三刀流 x 外資權威) ---
def get_v26_analysis(ticker):
    try:
        ticker = ticker.strip().upper()
        is_us = any(c.isalpha() for c in ticker)
        df = pd.DataFrame()
        tk_obj = None

        # 聖域路徑引導
        if is_us:
            tk_obj = yf.Ticker(ticker)
            df = tk_obj.history(period="2y", interval="1d", auto_adjust=True)
        else:
            for suf in [".TW", ".TWO"]:
                tmp = yf.download(f"{ticker}{suf}", period="2y", progress=False, auto_adjust=True)
                if not tmp.empty:
                    df, tk_obj = tmp, yf.Ticker(f"{ticker}{suf}")
                    break
        
        if df.empty or len(df) < 65: return None

        # 數據神聖化 (解決 MultiIndex 與 時區)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df.index = df.index.tz_localize(None)
        df = df.astype(float)

        # 刀神均線三刀流
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['MA60'] = ta.sma(df['Close'], length=60)
        macd = ta.macd(df['Close'])
        df['MACD_H'] = macd.iloc[:, 2] if macd is not None else 0
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        # 排除混沌 (dropna)
        df = df.dropna()
        if df.empty: return None
        
        last = df.iloc[-1]
        p, m5, m20, m60 = float(last['Close']), float(last['MA5']), float(last['MA20']), float(last['MA60'])
        
        # 籌碼與目標價 (印太戰略演算法)
        vol_avg = df['Volume'].rolling(20).mean().iloc[-1]
        vol_r = float(df['Volume'].iloc[-1] / vol_avg) if vol_avg > 0 else 1
        target_p = p * 1.08 if p > m20 and m20 > m60 else p * 1.04

        score = 0
        if p > m5: score += 20
        if p > m20: score += 40
        if m20 > m60: score += 20
        if float(last['MACD_H']) > 0: score += 10
        if vol_r > 1.2: score += 10

        status = "🟢【恩典強勢-啟航】" if score >= 85 and p > m5 else ("🔴【禁令警戒-避險】" if p < m20 or score < 55 else "🟡【曠野等待-盤整】")
        
        return {
            "df": df.tail(120), "score": score, "light": status, 
            "p": p, "m5": m5, "m20": m20, "m60": m60, "vol_r": vol_r, "target": target_p,
            "news": tk_obj.news[:2] if tk_obj and tk_obj.news else []
        }
    except: return None

# --- 3. 戰略回報系統 (徹底排除 KeyError) ---
def push_line(text):
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {TOKEN}"}
    payload = {"to":USER_ID, "messages":[{"type":"text", "text":text}]}
    try: requests.post("https://api.line.me/v2/bot/message/push", headers=headers, data=json.dumps(payload), timeout=10)
    except: pass

def send_v26_report(ticker, res, mode="診斷"):
    news_titles = "\n".join([f"▪️ {n.get('title','情報同步中')}" for n in res['news']]) if res['news'] else "無重大戰訊。"
    report = (f"🏛️ 國發 V26.0 聖域報報 - {mode}\n標的：{ticker}\n等級：{res['light']}\n"
              f"------------------\n現價：{res['p']:.2f} | 評分：{res['score']}\n"
              f"🎯 預期目標價：{res['target']:.2f}\n"
              f"------------------\n⚔️ 5MA攻擊：{res['m5']:.2f}\n🛡️ 20MA生命：{res['m20']:.2f}\n📈 60MA決策：{res['m60']:.2f}\n🔥 量能比：{res['vol_r']:.1f}x\n"
              f"------------------\n📰 關鍵情報摘要：\n{news_titles}")
    push_line(report)

# --- 4. 戰略指揮介面 ---
st.set_page_config(page_title="V26 聖域終極版", layout="wide")
st.title("🛡️ 國發投資終端 V26.0 (上帝權威版)")
st.caption("2026 印太戰略 x 刀神三刀流 | 全市場監控與強制回報系統")

# 個股診斷區
diag_t = st.text_input("💎 全球標的聖域診斷 (例: 00929, NVDA, 2330)", "00929").upper().strip()
if st.button("🚀 啟動聖域深度分析", use_container_width=True):
    with st.spinner("正在對標全球資本流動路徑..."):
        res = get_v26_analysis(diag_t)
        if res:
            st.subheader(f"{res['light']} {diag_t} | 戰略目標: {res['target']:.2f}")
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=res['df'].index, open=res['df']['Open'], high=res['df']['High'], low=res['df']['Low'], close=res['df']['Close'], name='K線'), row=1, col=1)
            fig.add_trace(go.Scatter(x=res['df'].index, y=res['df']['MA5'], line=dict(color='orange', width=1), name='5MA'), row=1, col=1)
            fig.add_trace(go.Scatter(x=res['df'].index, y=res['df']['MA20'], line=dict(color='#E91E63', width=2), name='20MA'), row=1, col=1)
            fig.add_trace(go.Scatter(x=res['df'].index, y=res['df']['MA60'], line=dict(color='#2196F3', width=2), name='60MA'), row=1, col=1)
            fig.update_layout(template="plotly_dark", height=650, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
            send_v26_report(diag_t, res)
        else: st.error("查無資料，請確認標的格式。")

# 監控按鈕
st.markdown("---")
st.header("⚡ 每日全市場獵鷹掃描 (強制結報)")
s1, s2, s3, s4 = st.columns(4)
SCAN_SEEDS = {
    "上市/ETF": ["0050.TW","00830.TW","00929.TW","2330.TW","2317.TW"],
    "美股強勢": ["VOO","NVDA","TSLA","AAPL","MSFT","PLTR"],
    "小資飆股": ["2344.TW","2409.TW","2618.TW","1605.TW"],
    "上櫃飆股": ["8046.TWO","6142.TWO","3163.TWO","6125.TWO","5483.TWO"]
}

def execute_mission(mode, stocks):
    st.info(f"正在執行 {mode} 戰略掃描...")
    bar = st.progress(0)
    found = []
    for i, t in enumerate(stocks):
        r = get_v26_analysis(t)
        if r and "🟢" in r['light']:
            found.append(t)
            send_v26_report(t, r, mode)
        bar.progress((i+1)/len(stocks))
        time.sleep(0.3)
    
    summary = f"🏛️ 聖域結報：{mode}\n✅ 任務完成。發現 {len(found)} 檔恩典綠燈標的。" if found else f"🏛️ 聖域結報：{mode}\n⚠️ 全場未發現綠燈。上帝之手提醒您：空手保本，等待公義的起漲。"
    push_line(summary)
    st.success(summary)

with s1:
    if st.button("📈 監控上市/ETF"): execute_mission("上市/ETF", SCAN_SEEDS["上市/ETF"])
with s2:
    if st.button("🇺🇸 監控美股強勢"): execute_mission("美股強勢", SCAN_SEEDS["美股強勢"])
with s3:
    if st.button("💰 偵測小資飆股"): execute_mission("小資飆股", SCAN_SEEDS["小資飆股"])
with s4:
    if st.button("🚀 偵測上櫃飆股", type="primary"): execute_mission("上櫃飆股", SCAN_SEEDS["上櫃飆股"])
