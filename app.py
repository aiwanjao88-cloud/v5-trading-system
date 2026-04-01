# -*- coding: utf-8 -*-
import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import json
import time
import plotly.graph_objects as go
from datetime import datetime

# --- 1. 固定金鑰 ---
TOKEN = "p0hZsq9njQwsK2QYkeTQjYYyJ87MpttosPY8E7e6HIbJns3Ii2AnYj4Z+QNaGCVrDphhuFlGKHJCnfMleQ1XlCJj2FRu2UJTYj9dAZUFIZfB4SLcVjXncnsGLrpflCwc1O3bU4OotJqW3zeslTFk8QdB04t89/1O/w1cDnyilFU="
USER_ID = "Ud25e9519467182c8b844df5260bccde5"

# --- 2. 核心邏輯 (加入 MA20/MA60 與 專業 K 線數據) ---

def get_optimized_data(ticker):
    try:
        is_us = any(c.isalpha() for c in ticker)
        suf = "" if is_us else (".TW" if len(ticker)<=4 else ".TWO")
        
        # 抓取 1 年資料以計算 60MA
        df = yf.download(f"{ticker}{suf}", period="1y", progress=False)
        if not is_us and df.empty:
            df = yf.download(f"{ticker}.TWO", period="1y", progress=False)
        
        if df.empty or len(df) < 60: return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df = df.astype(float)
        
        # 計算技術指標
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA20'] = ta.sma(df['Close'], length=20)   # 生命線
        df['MA60'] = ta.sma(df['Close'], length=60)   # 決策線
        macd = ta.macd(df['Close'])
        df['MACD'] = macd['MACD_12_26_9']
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        now = df.iloc[-1]
        p, m5, m20, m60 = float(now['Close']), float(now['MA5']), float(now['MA20']), float(now['MA60'])
        
        # 國發評分邏輯 (更嚴格，加入均線排列)
        score = 0
        if p > m5: score += 20
        if p > m20: score += 25
        if p > m60: score += 15
        if m5 > m20 > m60: score += 20  # 多頭排列
        if now['MACD'] > 0: score += 10
        if 50 < now['RSI'] < 70: score += 10
        
        # 紅綠燈判定
        light = "🟢【建議進場】" if score >= 85 and p > m20 else ("🔴【全面停損】" if p < m20 or score < 60 else "🟡【持有觀望】")
        url = f"https://tw.stock.yahoo.com/quote/{ticker}" if not is_us else f"https://finance.yahoo.com/quote/{ticker}"
        
        # 只保留最近 120 天繪圖用
        df_chart = df.tail(120)
        
        return {"df": df_chart, "score": score, "light": light, "p": p, "m5": m5, "m20": m20, "m60": m60, "url": url}
    except:
        return None

def send_line(msg):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {TOKEN}"}
    payload = {"to":USER_ID,"messages":[{"type":"text","text":f"🏛️ V10 國發戰報：\n{msg}"}]}
    try:
        requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
    except:
        pass

# --- 3. 繪圖引擎 (Plotly 互動式黑底K線圖) ---

def draw_v10_chart(ticker, df):
    # 建立 Candlestick K 線
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name='K線')])
    
    # 加入均線
    fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], line=dict(color='orange', width=1), name='5MA (短)'))
    fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], line=dict(color='magenta', width=2), name='20MA (生命)'))
    fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], line=dict(color='cyan', width=2), name='60MA (季)'))
    
    # 佈局美化
    fig.update_layout(
        title=f"{ticker} 技術面診斷 (MA20生命線: {df['MA20'][-1]:.1f})",
        yaxis_title="價格",
        template="plotly_dark",  # 黑底，更有科技感
        height=500,
        xaxis_rangeslider_visible=False,  # 隱藏下方拉條讓畫面乾淨
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    # 繪製圖表至 Streamlit
    st.plotly_chart(fig, use_container_width=True)

# --- 4. 介面設計 ---

st.set_page_config(page_title="V10 專業技術終端", layout="wide")
st.title("🛡️ V10 國發級投資終端 (技術分析圖表版)")
st.markdown("---")

# --- A. 個股深度診斷與繪圖區 ---
st.header("🔍 個股深度檢診 (含 MA20/60 K線)")
c_in, c_btn = st.columns([3,1])
with c_in:
    diag_t = st.text_input("輸入代碼 (2317 或 NVDA)", "2317").strip().upper()
with c_btn:
    st.write("<br>", unsafe_allow_html=True)
    if st.button("🚀 執行深度檢診", use_container_width=True):
        with st.spinner("正在下載大數據並繪製技術圖表..."):
            res = get_optimized_data(diag_t)
            if res:
                st.subheader(f"📊 {diag_t} 報告 (得分: {res['score']})")
                
                # --- [優化核心]：在 App 上繪製互動式 K 線圖 ---
                draw_v10_chart(diag_t, res['df'])
                
                # 文字報告
                col1, col2 = st.columns(2)
                with col1:
                    st.success("🟢 進場建議")
                    msg_in = "站穩 MA5，且符合評分，動能強勁！" if (res['score']>=80 and res['p']>res['m5']) else f"建議等站穩 {res['m5']:.2f} (5MA) 再進場。"
                    st.write(msg_in)
                with col2:
                    st.error("🔴 出場建議")
                    st.write(f"1. 短線止損: {res['p']*0.93:.2f} (7%)")
                    st.write(f"2. 波段出場:有效跌破 **{res['m20']:.2f} (生命線)**")
                
                # LINE 推播
                report = f"{res['light']}\n標的：{diag_t}\n現價：{res['p']:.2f}\n生命線(20MA)：{res['m20']:.2f}\n決策線(60MA)：{res['m60']:.2f}\n📊線圖：https://finance.yahoo.com/quote/{diag_t}"
                send_line(report)
            else:
                st.error("查無資料或資料不足(需60日以上)。")

# --- B. 策略自動監控區 ---
st.markdown("---")
st.header("🚀 策略自動監控面板")
b1, b2, b3, b4 = st.columns(4)

def run_scan_v10(stocks, mode):
    bar = st.progress(0)
    for i, t in enumerate(stocks):
        r = get_optimized_data(t)
        # 美股強勢門檻拉高，小資櫃買重動能
        threshold = 85 if mode == "美股" else 80
        if r and "🟢" in r['light'] and r['score'] >= threshold:
            send_line(f"🚨【{mode}飆股】{t}\n評分:{r['score']}\n價格:{r['p']:.2f}\nMA20:{r['m20']:.2f}\n📊看圖:https://tw.stock.yahoo.com/quote/{t}")
        bar.progress((i+1)/len(stocks))
        time.sleep(0.1)
    st.success(f"{mode} 監控完成")

with b1:
    if st.button("📈 上市波段", use_container_width=True):
        run_scan_v10(["2330","2317","2454","2382","2603"], "上市波段")
with b2:
    if st.button("🇺🇸 美股強勢", use_container_width=True):
        run_scan_v10(["NVDA","TSLA","AAPL","AMD","PLTR","COIN"], "美股")
with b3:
    if st.button("💰 小資飆股", use_container_width=True):
        run_scan_v10(["2344","2363","2409","3481","2618","1605"], "小資")
with b4:
    if st.button("💎 上櫃飆股", type="primary", use_container_width=True):
        # 鎖定 10-60 元櫃買股
        run_scan_v10(["8046","6142","3234","3163","4533","6125","5483","6290","8064"], "上櫃")
