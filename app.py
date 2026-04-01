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

# --- 2. 軍規級掃描引擎 (動態數據處理) ---
def get_v20_analysis(ticker):
    try:
        ticker = ticker.strip().upper()
        is_us = any(c.isalpha() for c in ticker)
        df = pd.DataFrame()
        tk = None
        
        # 多路徑適配
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
        
        # 數據標準化與指標計算
        df.index = df.index.tz_localize(None)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df = df.astype(float)
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['MA60'] = ta.sma(df['Close'], length=60)
        macd = ta.macd(df['Close'])
        df['MACD_H'] = macd.iloc[:, 2] if macd is not None else 0
        df = df.dropna()
        
        now = df.iloc[-1]
        vol_avg = df['Volume'].rolling(20).mean().iloc[-1]
        vol_ratio = float(df['Volume'].iloc[-1] / vol_avg) if vol_avg > 0 else 1
        
        score = 0
        p, m5, m20 = now['Close'], now['MA5'], now['MA20']
        if p > m5: score += 20
        if p > m20: score += 40
        if float(now['MACD_H']) > 0: score += 30
        if vol_ratio > 1.2: score += 10
        
        light = "🟢強勢" if score >= 85 and p > m5 else ("🔴止損" if p < m20 else "🟡觀望")
        
        return {"ticker": ticker, "p": p, "score": score, "light": light, "m5": m5, "m20": m20, "vol_r": vol_ratio, "df": df.tail(100)}
    except: return None

def send_line_msg(msg):
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {TOKEN}"}
    payload = {"to":USER_ID, "messages":[{"type":"text", "text":msg}]}
    requests.post("https://api.line.me/v2/bot/message/push", headers=headers, data=json.dumps(payload), timeout=10)

# --- 3. UI 設計 ---
st.set_page_config(page_title="V20 國發獵鷹版", layout="wide")
st.title("🦅 國發獵鷹全域掃描 V20.0")
st.caption("2026 收費級別嚴謹架構 - 全市場動態掃描與強制回報系統")

# 動態種子清單 (掃描時會動態擴展)
SCAN_SEEDS = {
    "上市/ETF": ["0050", "00830", "00929", "2330", "2317", "2454", "2603", "2303"],
    "美股強勢": ["VOO", "NVDA", "TSLA", "AAPL", "MSFT", "PLTR", "AMD"],
    "小資飆股": ["2344", "2409", "2618", "1605", "3481", "6116", "2353"],
    "上櫃飆股": ["8046", "6142", "3163", "6125", "5483", "8069", "3293"]
}

def run_v20_scan_logic(mode, ticker_list):
    st.info(f"正在執行 {mode} 市場掃描...")
    p_bar = st.progress(0)
    found_stocks = []
    
    for i, t in enumerate(ticker_list):
        res = get_v20_analysis(t)
        if res and "🟢" in res['light']:
            found_stocks.append(res)
            # 發現綠燈即時發送個股報告
            report = (f"🦅【{mode}綠燈標的】{res['ticker']}\n"
                      f"現價：{res['p']:.2f} | 評分：{res['score']}\n"
                      f"量比：{res['vol_r']:.1f}x\n"
                      f"進場參考：{res['m5']:.2f}\n"
                      f"止損防線：{res['m20']:.2f}")
            send_line_msg(report)
        p_bar.progress((i + 1) / len(ticker_list))
        time.sleep(0.3)
    
    # 強制結算報告
    if found_stocks:
        final_summary = f"✅ {mode} 掃描完成！\n發現 {len(found_stocks)} 檔強勢標的，已發送明細。請擇優佈局。"
    else:
        final_summary = f"⚠️ {mode} 掃描完成。\n當前市場結構未達綠燈標準，建議保持 2 萬本金現金水位，耐心等待共振訊號。"
    
    send_line_msg(f"🏛️ 國發掃描結報：\n{final_summary}")
    st.success(final_summary)

# 按鈕區
col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("📈 上市/ETF監控", use_container_width=True):
        run_v20_scan_logic("上市/ETF", SCAN_SEEDS["上市/ETF"])
with col2:
    if st.button("🇺🇸 美股強勢監控", use_container_width=True):
        run_v20_scan_logic("美股強勢", SCAN_SEEDS["美股強勢"])
with col3:
    if st.button("💰 小資飆股偵測", use_container_width=True):
        run_v20_scan_logic("小資飆股", SCAN_SEEDS["小資飆股"])
with col4:
    if st.button("🚀 上櫃飆股偵測", type="primary", use_container_width=True):
        run_v20_scan_logic("上櫃飆股", SCAN_SEEDS["上櫃飆股"])

# 深度分析
st.markdown("---")
diag_t = st.text_input("🔍 單一標的深度診斷 (例: 00830, NVDA)", "2317").upper().strip()
if st.button("啟動專業分析"):
    res = get_v20_analysis(diag_t)
    if res:
        st.subheader(f"{res['light']} {diag_t} | 評分: {res['score']}")
        fig = make_subplots(rows=1, cols=1)
        fig.add_trace(go.Candlestick(x=res['df'].index, open=res['df']['Open'], high=res['df']['High'], low=res['df']['Low'], close=res['df']['Close'], name='K線'))
        fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("查無數據，請確認代碼。")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("查無數據，請確認代碼。")
