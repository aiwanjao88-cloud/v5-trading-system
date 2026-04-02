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

# --- 2. 鋼鐵核心引擎 (修正所有報錯邏輯) ---
def get_v29_core_logic(ticker):
    try:
        ticker = ticker.strip().upper()
        is_us = any(c.isalpha() for c in ticker)
        df = pd.DataFrame()
        
        # 多重數據路由
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

        # 數據結構清洗 (解決 MultiIndex 與時區)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df.index = df.index.tz_localize(None)
        df = df.astype(float)

        # 刀神均線三刀流
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['MA60'] = ta.sma(df['Close'], length=60)
        macd = ta.macd(df['Close'])
        df['MACD_H'] = macd.iloc[:, 2] if macd is not None else 0
        df = df.dropna()
        
        now = df.iloc[-1]
        p, m20 = float(now['Close']), float(now['MA20'])
        vol_avg = df['Volume'].rolling(20).mean().iloc[-1]
        vol_r = float(df['Volume'].iloc[-1] / vol_avg) if vol_avg > 0 else 1
        
        # 10% 獲利回收價
        target_p = p * 1.10
        
        # 戰略評分
        score = 0
        if p > float(now['MA5']): score += 20
        if p > m20: score += 40
        if m20 > float(now['MA60']): score += 20
        if float(now['MACD_H']) > 0: score += 20

        status = "🟢強勢" if score >= 80 else ("🔴止損" if p < m20 else "🟡觀望")
        
        return {
            "ticker": ticker, "p": p, "target": target_p, "m20": m20, 
            "vol_r": vol_r, "status": status, "url": chart_url, "score": score
        }
    except: return None

def push_v29_line(text):
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {TOKEN}"}
    payload = {"to":USER_ID, "messages":[{"type":"text", "text":text}]}
    try: requests.post("https://api.line.me/v2/bot/message/push", headers=headers, data=json.dumps(payload), timeout=10)
    except: pass

# --- 3. 聖域介面 (修正 SyntaxError 與 縮排) ---
st.set_page_config(page_title="V29 聖域盤石版", layout="wide")
st.title("🛡️ 國發聖域終端 V29.0 (上帝盤石穩定版)")
st.caption("2026 印太戰略操盤手專用 | 自訂 20 欄位 10% 獲利監控與圖表連結")

# [A] 20 欄位自訂監控區
st.header("📋 24H 戰略監控清單 (20 欄位)")
custom_input = st.text_area("輸入代碼 (逗號分隔)", "00830, 00919, 00929, 2330, NVDA, TSM, VOO, TSLA, SMH, QQQM").upper()

if st.button("🚀 啟動即時監控 (含 10% 獲利預估)", use_container_width=True):
    tickers = [t.strip() for t in custom_input.split(",") if t.strip()][:20]
    data_log = []
    for t in tickers:
        res = get_v29_core_logic(t)
        if res:
            data_log.append(res)
            # LINE 同步
            report = (f"🏛️ V29 監控：{res['ticker']}\n狀態：{res['status']}\n現價：{res['p']:.2f}\n"
                      f"🎯 10%回收：{res['target']:.2f}\n🛡️ 生命線：{res['m20']:.2f}\n📊 線圖：{res['url']}")
            push_v29_line(report)
    
    if data_log:
        df_final = pd.DataFrame(data_log)[['ticker', 'status', 'p', 'target', 'm20', 'vol_r']]
        df_final.columns = ['代碼', '狀態', '市價', '10%回收點', '生命線', '量比']
        st.table(df_final)

# [B] 原有條件掃描 (修復 Sea-horse 語法)
st.markdown("---")
st.header("⚡ 全市場戰略掃描 (原有條件不變)")
c1, c2, c3, c4 = st.columns(4)

def run_v29_scan(mode, list_stocks):
    st.info(f"掃描 {mode} 中...")
    found_count = 0
    for t in list_stocks:
        r = get_v29_core_logic(t)
        if r and "🟢" in r['status']:
            msg = f"🦅 V29 {mode}綠燈：{r['ticker']}\n現價：{r['p']:.2f}\n目標：{r['target']:.2f}\n📊 線圖：{r['url']}"
            push_v29_line(msg)
            found_count += 1
    st.success(f"任務完成。發現 {found_count} 檔強勢標的。")

with c1:
    if st.button("📈 監控上市波段"):
        run_v29_scan("上市", ["2330","2317","2454","2382","2603"])
with c2:
    if st.button("🇺🇸 監控美股強勢"):
        run_v29_scan("美股", ["NVDA","TSLA","PLTR","COIN","AMD"])
with c3:
    if st.button("💰 偵測小資飆股"):
        run_v29_scan("小資", ["2344","2409","2618","3481","6116"])
with c4:
    if st.button("🚀 偵測上櫃飆股", type="primary"):
        run_v29_scan("上櫃", ["8046","6142","3234","3163","8069"])
