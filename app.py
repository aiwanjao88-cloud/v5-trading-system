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

# --- 1. 核心參數與環境初始化 ---
TOKEN = "p0hZsq9njQwsK2QYkeTQjYYyJ87MpttosPY8E7e6HIbJns3Ii2AnYj4Z+QNaGCVrDphhuFlGKHJCnfMleQ1XlCJj2FRu2UJTYj9dAZUFIZfB4SLcVjXncnsGLrpflCwc1O3bU4OotJqW3zeslTFk8QdB04t89/1O/w1cDnyilFU="
USER_ID = "Ud25e9519467182c8b844df5260bccde5"

st.set_page_config(page_title="V13 鋼鐵穩定終端", layout="wide")

# --- 2. 數據獲取引擎 (防禦性增強) ---
def get_v13_data(ticker):
    try:
        is_us = any(c.isalpha() for c in ticker)
        ticker = ticker.strip().upper()
        
        # 多重後綴嘗試邏輯
        suffixes = ["", ".TW", ".TWO"] if not is_us else [""]
        df = pd.DataFrame()
        
        for suf in suffixes:
            temp_df = yf.download(f"{ticker}{suf}", period="1y", interval="1d", progress=False)
            if not temp_df.empty:
                df = temp_df
                break
        
        if df.empty or len(df) < 60:
            return None
        
        # 強制展開 MultiIndex (yfinance 0.2.x 穩定法)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df = df.astype(float)
        
        # 指標計算
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['MA60'] = ta.sma(df['Close'], length=60)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        macd = ta.macd(df['Close'])
        if macd is not None:
            df['MACD'] = macd['MACD_12_26_9']
        else:
            df['MACD'] = 0
            
        # [關鍵] 移除所有 NaN，確保索引絕對對齊
        clean_df = df.dropna().copy()
        if clean_df.empty: return None
        
        now = clean_df.iloc[-1]
        p, m5, m20, m60 = now['Close'], now['MA5'], now['MA20'], now['MA60']
        
        # 國發管理人策略評分
        score = 0
        if p > m5: score += 25
        if p > m20: score += 25
        if m20 > m60: score += 20
        if now['MACD'] > 0: score += 20
        if 50 < now['RSI'] < 75: score += 10
        
        light = "🟢【強勢起飛】" if score >= 85 and p > m20 else ("🔴【防禦撤退】" if p < m20 or score < 55 else "🟡【等待訊號】")
        mdj_url = f"https://www.moneydj.com/KMDJ/Search/SearchViewer.aspx?search={ticker}" if not is_us else f"https://finance.yahoo.com/quote/{ticker}"
        
        return {
            "df": clean_df.tail(100), "score": int(score), "light": light, 
            "p": p, "m5": m5, "m20": m20, "m60": m60, "mdj": mdj_url
        }
    except Exception as e:
        return None

def send_line(msg):
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {TOKEN}"}
    payload = {"to":USER_ID,"messages":[{"type":"text","text":f"🏛️ 國發 V13 戰略訊號：\n{msg}"}]}
    try: requests.post("https://api.line.me/v2/bot/message/push", headers=headers, data=json.dumps(payload), timeout=5)
    except: pass

# --- 3. TradingView 穩定繪圖引擎 ---
def draw_v13_chart(ticker, df):
    try:
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
        # K線主圖
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='#E91E63', width=2), name='生命線'), row=1, col=1)
        
        # 成交量
        colors = ['#26a69a' if df['Close'].iloc[i] >= df['Open'].iloc[i] else '#ef5350' for i in range(len(df))]
        fig.add_trace(go.Bar(x=df.index, y=df['Volume'], marker_color=colors, name='量能'), row=2, col=1)
        
        fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False, margin=dict(t=30, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)
    except:
        st.warning("⚠️ 圖表渲染異常，請參考文字數據。")

# --- 4. 戰略介面 ---
st.title("🛡️ 國發級戰略終端 V13.0 (鋼鐵穩定版)")
st.markdown("---")

# 檢診模組
c_in, c_btn = st.columns([3,1])
with c_in: diag_t = st.text_input("輸入代碼 (2330, 00929, TSLA)", "00929").strip()
with c_btn:
    st.write("<br>", unsafe_allow_html=True)
    if st.button("🚀 執行深度檢診", use_container_width=True):
        res = get_v13_data(diag_t)
        if res:
            st.subheader(f"{res['light']} {diag_t} | 評分: {res['score']}")
            col1, col2 = st.columns(2)
            with col1: st.info(f"📰 [MoneyDJ 法人情報點此]({res['mdj']})")
            with col2: st.warning(f"⚖️ 進場參考: {res['m5']:.2f} | 止損防線: {res['m20']:.2f}")
            draw_v13_chart(diag_t, res['df'])
            send_line(f"{res['light']}\n標的：{diag_t}\n現價：{res['p']:.2f}\n評分：{res['score']}")
        else:
            st.error("❌ 無法獲取有效數據。請檢查：1.代碼是否正確 2.網路連線 3.該股是否剛上市資料不足。")

# 監控模組
st.markdown("### ⚡ 紅綠燈戰略掃描")
b1, b2, b3, b4 = st.columns(4)

def run_v13_scan(stocks, mode):
    bar = st.progress(0)
    for i, t in enumerate(stocks):
        r = get_v13_data(t)
        if r and "🟢" in r['light']:
            send_line(f"🚨【{mode}綠燈】{t}\n價格：{r['p']:.2f}\n評分：{r['score']}")
        bar.progress((i+1)/len(stocks))
    st.success(f"{mode} 監控任務圓滿完成")

with b1:
    if st.button("📈 上市/ETF監控", use_container_width=True):
        run_v13_scan(["00830","0050","00929","2330","2317"], "波段股")
with b2:
    if st.button("🇺🇸 美股強勢監控", use_container_width=True):
        run_v13_scan(["NVDA","TSLA","PLTR","AAPL","GOOGL"], "美股")
with b3:
    if st.button("💰 小資飆股偵測", use_container_width=True):
        run_scan = run_v13_scan(["2344","2409","2618","1605","2353"], "小資")
with b4:
    if st.button("🚀 上櫃飆股偵測", type="primary", use_container_width=True):
        run_v13_scan(["8046","6142","3163","6125","5483","3264"], "上櫃飆")
