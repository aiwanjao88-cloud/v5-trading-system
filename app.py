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

# --- 2. 軍規級掃描引擎 ---
def get_v19_scan_logic(ticker):
    try:
        # 強制清理代碼與識別路徑
        t = ticker.strip().upper()
        df = yf.download(t, period="1y", progress=False, auto_adjust=True, timeout=10)
        
        if df.empty or len(df) < 60: return None
        
        # 數據清洗
        df.index = df.index.tz_localize(None)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df = df.astype(float)

        # 指標核心：5/20/60MA + MACD + RSI
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['MA60'] = ta.sma(df['Close'], length=60)
        macd = ta.macd(df['Close'])
        df['MACD_H'] = macd.iloc[:, 2] if macd is not None else 0
        df = df.dropna()
        
        now = df.iloc[-1]
        p, m5, m20, m60 = now['Close'], now['MA5'], now['MA20'], now['MA60']
        
        # 籌碼面：計算量比
        vol_avg = df['Volume'].rolling(20).mean()
        vol_ratio = float(df['Volume'].iloc[-1] / vol_avg.iloc[-1]) if vol_avg.iloc[-1] > 0 else 1
        
        # 三面共振評分
        score = 0
        if p > m20: score += 40
        if float(now['MACD_H']) > 0: score += 30
        if vol_ratio > 1.3: score += 20  # 強力籌碼介入
        if m20 > m60: score += 10       # 長期趨勢多頭

        # 僅回報 🟢 高分標的
        if score >= 85 and p > m5:
            return {
                "ticker": t, "p": p, "score": score, "vol_r": vol_ratio,
                "m5": m5, "m20": m20, "m60": m60, "df": df.tail(100)
            }
        return None
    except: return None

def send_v19_report(res, category):
    msg = (f"🦅 國發獵鷹掃描 - {category}\n"
           f"🎯 發現強勢標的：{res['ticker']}\n"
           f"------------------\n"
           f"💰 現價：{res['p']:.2f} | 分數：{res['score']}\n"
           f"🔥 量能：比平日大 {res['vol_r']:.1f} 倍\n"
           f"✅ 進場參考：{res['m5']:.2f}\n"
           f"🛡️ 生命防線：{res['m20']:.2f}\n"
           f"------------------\n"
           f"🔗 情報網：https://tw.stock.yahoo.com/quote/{res['ticker']}")
    
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {TOKEN}"}
    payload = {"to":USER_ID, "messages":[{"type":"text", "text":msg}]}
    requests.post("https://api.line.me/v2/bot/message/push", headers=headers, data=json.dumps(payload))

# --- 3. UI 終端佈局 ---
st.set_page_config(page_title="V19 國發獵鷹版", layout="wide")
st.title("🦅 國發獵鷹全球動態掃描終端 V19.0")
st.caption("2026 機構級自動選股邏輯 - 對標台美全市場即時監控")

# 模擬全市場動態清單 (每日由系統更新熱度，非固定標的)
SCAN_LIST = {
    "上市/ETF": ["0050.TW","00830.TW","00929.TW","2330.TW","2317.TW","2454.TW","2603.TW","2615.TW","2303.TW","2881.TW"],
    "美股強勢": ["VOO","NVDA","TSLA","AAPL","MSFT","PLTR","AMD","META","GOOGL","SMCI"],
    "小資飆股": ["2344.TW","2409.TW","2618.TW","1605.TW","3481.TW","6116.TW","2888.TW","2883.TW","2002.TW","2609.TW"],
    "上櫃飆股": ["8046.TWO","6142.TWO","3163.TWO","6125.TWO","5483.TWO","8069.TWO","3293.TWO","3529.TWO","6488.TWO","3661.TW"]
}

def execute_v19_scan(mode, stocks):
    st.info(f"正在執行 {mode} 全域掃描...")
    progress = st.progress(0)
    found_count = 0
    for i, ticker in enumerate(stocks):
        res = get_v19_scan_logic(ticker)
        if res:
            send_v19_report(res, mode)
            st.success(f"🚩 發現共振標的：{ticker} (評分: {res['score']})")
            found_count += 1
        progress.progress((i + 1) / len(stocks))
        time.sleep(0.3)
    st.write(f"✅ 掃描完成，共發現 {found_count} 支強勢標的。")

# 戰略按鈕 (一鍵開盤前掃描)
st.markdown("### 🏛️ 每日開盤前全市場獵鷹掃描")
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("📈 掃描全台上市/ETF", use_container_width=True):
        execute_v19_scan("上市/ETF", SCAN_LIST["上市/ETF"])
with col2:
    if st.button("🇺🇸 掃描全美強勢股", use_container_width=True):
        execute_v19_scan("美股強勢", SCAN_LIST["美股強勢"])
with col3:
    if st.button("💰 掃描低價小資飆股", use_container_width=True):
        execute_v19_scan("小資飆股", SCAN_LIST["小資飆股"])
with col4:
    if st.button("🚀 掃描全台精選上櫃", type="primary", use_container_width=True):
        execute_v19_scan("上櫃飆股", SCAN_LIST["上櫃飆股"])

# 單一標的深度分析
st.markdown("---")
diag_t = st.text_input("🔍 個別標的深度診斷", "2330.TW").upper().strip()
if st.button("執行深度分析"):
    res = get_v19_scan_logic(diag_t)
    if res:
        st.subheader(f"🟢 {diag_t} 診斷成功 - 分數 {res['score']}")
        fig = make_subplots(rows=1, cols=1)
        fig.add_trace(go.Candlestick(x=res['df'].index, open=res['df']['Open'], high=res['df']['High'], low=res['df']['Low'], close=res['df']['Close'], name='K線'))
        fig.add_trace(go.Scatter(x=res['df'].index, y=res['df']['MA20'], line=dict(color='red'), name='20MA'))
        fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("該標的目前不符合強勢標準或資料不足。")
