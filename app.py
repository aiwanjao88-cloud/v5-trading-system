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

# --- 2. 鋼鐵級分析引擎 (修復 MultiIndex 與時區問題) ---
def get_v22_ultra_data(ticker):
    try:
        ticker = ticker.strip().upper()
        # 自動識別美股與台股路徑
        is_us = any(c.isalpha() for c in ticker)
        df = pd.DataFrame()
        tk_obj = None

        if is_us:
            tk_obj = yf.Ticker(ticker)
            df = tk_obj.history(period="2y", auto_adjust=True)
        else:
            # 強力台股識別：優先補 TW，失敗則嘗試 TWO
            for suf in [".TW", ".TWO"]:
                df_trial = yf.download(f"{ticker}{suf}", period="2y", progress=False, auto_adjust=True)
                if not df_trial.empty:
                    df = df_trial
                    tk_obj = yf.Ticker(f"{ticker}{suf}")
                    break
        
        if df.empty or len(df) < 65: return None

        # [修復重點] 展平 MultiIndex 並移除時區
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.index = df.index.tz_localize(None)
        df = df.astype(float)

        # 指標計算
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['MA60'] = ta.sma(df['Close'], length=60)
        macd = ta.macd(df['Close'])
        df['MACD_H'] = macd.iloc[:, 2] if macd is not None else 0
        
        # 徹底移除 NaN 確保索引絕對對齊 (防止 KeyError)
        df = df.dropna()
        if df.empty: return None
        
        latest = df.iloc[-1]
        p, m20 = float(latest['Close']), float(latest['MA20'])
        
        # 籌碼面：量比
        vol_avg = df['Volume'].rolling(20).mean().iloc[-1]
        vol_r = float(df['Volume'].iloc[-1] / vol_avg) if vol_avg > 0 else 1

        # 評分與紅綠燈
        score = 0
        if p > float(latest['MA5']): score += 30
        if p > m20: score += 40
        if float(latest['MACD_H']) > 0: score += 20
        if vol_r > 1.2: score += 10
        
        light = "🟢強勢" if score >= 85 and p > float(latest['MA5']) else ("🔴止損" if p < m20 else "🟡觀望")
        
        # 修正 MoneyDJ 搜尋路徑
        mdj = f"https://www.moneydj.com/KMDJ/Common/ListNewNews.aspx?index=1&search={ticker}"
        
        return {
            "df": df.tail(100), "score": score, "light": light, 
            "p": p, "m5": latest['MA5'], "m20": m20, "m60": latest['MA60'],
            "vol_r": vol_r, "mdj": mdj, "news": tk_obj.news[:2] if tk_obj and tk_obj.news else []
        }
    except: return None

def send_line(msg):
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {TOKEN}"}
    payload = {"to":USER_ID, "messages":[{"type":"text", "text":msg}]}
    requests.post("https://api.line.me/v2/bot/message/push", headers=headers, data=json.dumps(payload), timeout=10)

# --- 3. UI 終端設計 ---
st.set_page_config(page_title="V22 國發終極版", layout="wide")
st.title("🛡️ 國發終極穩定終端 V22.0")
st.caption("2026 全市場動態掃描 - 修復 00929/NVDA 數據對齊問題")

# 深度檢診區
diag_t = st.text_input("🔍 輸入全球標的代碼 (00929, 2317, NVDA)", "00929").upper().strip()
if st.button("🚀 執行深度戰略分析", use_container_width=True):
    res = get_v22_ultra_data(diag_t)
    if res:
        st.subheader(f"{res['light']} {diag_t} | 評分: {res['score']}")
        
        # 專業 K 線圖 (包含 5/20/60MA)
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=res['df'].index, open=res['df']['Open'], high=res['df']['High'], low=res['df']['Low'], close=res['df']['Close'], name='K線'), row=1, col=1)
        fig.add_trace(go.Scatter(x=res['df'].index, y=res['df']['MA5'], line=dict(color='orange', width=1), name='5MA'), row=1, col=1)
        fig.add_trace(go.Scatter(x=res['df'].index, y=res['df']['MA20'], line=dict(color='#E91E63', width=2), name='20MA'), row=1, col=1)
        fig.add_trace(go.Scatter(x=res['df'].index, y=res['df']['MA60'], line=dict(color='#2196F3', width=2), name='60MA'), row=1, col=1)
        
        colors = ['#26a69a' if res['df']['Close'].iloc[i] >= res['df']['Open'].iloc[i] else '#ef5350' for i in range(len(res['df']))]
        fig.add_trace(go.Bar(x=res['df'].index, y=res['df']['Volume'], marker_color=colors, name='量能'), row=2, col=1)
        fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
        
        # 推播
        report = f"🏛️ V22 戰報：{diag_t}\n現價：{res['p']:.2f}\n進場：{res['m5']:.2f}\n止損：{res['m20']:.2f}\n情報：{res['mdj']}"
        send_line(report)
    else:
        st.error("查無資料，請確認代碼無誤。")

# 動態掃描清單
SCAN_LISTS = {
    "上市/ETF": ["0050.TW","00830.TW","00929.TW","2330.TW","2317.TW"],
    "美股強勢": ["VOO","NVDA","TSLA","AAPL","PLTR"],
    "小資飆股": ["2344.TW","2409.TW","2618.TW","1605.TW"],
    "上櫃飆股": ["8046.TWO","6142.TWO","3163.TWO","6125.TWO"]
}

st.markdown("---")
st.header("⚡ 戰略綠燈強制回報監控")
c1, c2, c3, c4 = st.columns(4)

def run_v22_scan(mode, stocks):
    st.info(f"正在掃描 {mode} 市場...")
    p = st.progress(0)
    found = []
    for i, t in enumerate(stocks):
        r = get_v22_ultra_data(t)
        if r and "🟢" in r['light']:
            found.append(r)
            send_line(f"🚨【{mode}-綠燈】{r['ticker']}\n價：{r['p']:.2f}\n評分：{r['score']}\n止損：{r['m20']:.2f}")
        p.progress((i+1)/len(stocks))
        time.sleep(0.3)
    
    summary = f"✅ {mode} 掃描完畢！共發現 {len(found)} 檔綠燈標的。" if found else f"⚠️ {mode} 掃描完畢，未發現強勢標的，建議空手保護 2 萬本金。"
    send_line(f"🏛️ 國發結報：\n{summary}")
    st.success(summary)

with c1:
    if st.button("📈 上市/ETF監控"): run_v22_scan("上市/ETF", SCAN_LISTS["上市/ETF"])
with c2:
    if st.button("🇺🇸 美股強勢監控"): run_v22_scan("美股強勢", SCAN_LISTS["美股強勢"])
with c3:
    if st.button("💰 小資飆股偵測"): run_v22_scan("小資飆股", SCAN_LISTS["小資飆股"])
with c4:
    if st.button("🚀 上櫃飆股偵測", type="primary"): run_v22_scan("上櫃飆股", SCAN_LISTS["上櫃飆股"])
