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

# --- 2. 機構級分析引擎 (對標收費軟體數據精度) ---
def get_v16_premium_analysis(ticker):
    try:
        ticker = ticker.strip().upper()
        is_us = any(c.isalpha() for c in ticker)
        
        df = pd.DataFrame()
        tk = None
        
        # 數據抓取：自動路徑切換
        if is_us:
            tk = yf.Ticker(ticker)
            df = tk.history(period="1y", interval="1d", auto_adjust=True)
        else:
            for suffix in [".TW", ".TWO"]:
                temp_df = yf.download(f"{ticker}{suffix}", period="1y", progress=False, auto_adjust=True)
                if not temp_df.empty:
                    df = temp_df
                    tk = yf.Ticker(f"{ticker}{suffix}")
                    break

        if df.empty or len(df) < 60: return None

        # 數據清洗：移除時區與展平索引 (核心穩定性優化)
        df.index = df.index.tz_localize(None)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.astype(float)

        # 指標計算：對標機構參數
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['MA60'] = ta.sma(df['Close'], length=60)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        macd = ta.macd(df['Close'])
        # 安全存取 MACD 柱狀圖
        df['MACD_H'] = macd.iloc[:, 2] if macd is not None else 0
        
        # 籌碼面：量比分析 (量增價揚判定)
        vol_avg = df['Volume'].rolling(20).mean()
        vol_ratio = float(df['Volume'].iloc[-1] / vol_avg.iloc[-1]) if vol_avg.iloc[-1] > 0 else 1

        # 情報摘要 (對標 Alpha Vantage 新聞接口)
        safe_news = []
        try:
            raw_news = tk.news[:3]
            for n in raw_news:
                title = n.get('title') or n.get('headline') or "精選產業情報"
                safe_news.append(title)
        except: pass

        df_clean = df.dropna()
        if df_clean.empty: return None
        now = df_clean.iloc[-1]
        
        # 三位一體評分權重
        score = 0
        p, m5, m20 = float(now['Close']), float(now['MA5']), float(now['MA20'])
        if p > m20: score += 40               # 技術面：守住生命線
        if float(now['MACD_H']) > 0: score += 30 # 動能面：紅柱增長
        if vol_ratio > 1.2: score += 20       # 籌碼面：主力介入
        if 50 < float(now['RSI']) < 75: score += 10 # 心理面：強勢區
        
        light = "🟢【機構級強勢標的】" if score >= 85 and p > m5 else ("🔴【絕對風險止損】" if p < m20 or score < 50 else "🟡【區間結構整理】")
        
        return {
            "df": df_clean.tail(100), "score": score, "light": light, 
            "p": p, "m5": m5, "m20": m20, "vol_r": vol_ratio, "news": safe_news,
            "mdj": f"https://www.moneydj.com/KMDJ/Search/SearchViewer.aspx?search={ticker}"
        }
    except: return None

def send_v16_line(ticker, res):
    news_text = ""
    for i, title in enumerate(res['news']):
        news_text += f" {i+1}. {title}\n"
    if not news_text: news_text = "目前暫無重大新聞披露。"

    msg = (f"🏛️ 國發 V16.0 戰略戰報\n標的：{ticker}\n級別：{res['light']}\n"
           f"------------------\n現價：{res['p']:.2f} | 總分：{res['score']}\n"
           f"📊 籌碼量比：{res['vol_r']:.1f}\n"
           f"------------------\n✅ 進場參考：{res['m5']:.2f}\n❌ 止損防線：{res['m20']:.2f}\n"
           f"------------------\n📰 即時情報摘要：\n{news_text}\n"
           f"🔗 深度情報：{res['mdj']}")
    
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {TOKEN}"}
    payload = {"to":USER_ID, "messages":[{"type":"text", "text":msg}]}
    try: requests.post("https://api.line.me/v2/bot/message/push", headers=headers, data=json.dumps(payload), timeout=10)
    except: pass

# --- 3. 專業級 UI 佈局 ---
st.set_page_config(page_title="V16.0 國發終端", layout="wide")
st.title("🛡️ 國發級投資終端 V16.0 (機構級嚴謹版)")

with st.sidebar:
    st.header("🛠️ 專業選股工具箱")
    st.markdown("- [財報狗](https://statementdog.com/) (基本面體質)")
    st.markdown("- [Yahoo股市選股](https://tw.stock.yahoo.com/screener/) (指標篩選)")
    st.markdown("- [XQ官方部落格](https://www.xq.com.tw/blog/) (量化邏輯)")

diag_t = st.text_input("🔍 輸入全球標的代碼 (VOO, NVDA, 2317, 00830)", "2317").upper().strip()

if st.button("🚀 啟動三位一體戰略檢診", use_container_width=True):
    with st.spinner("正在執行多維度數據校準..."):
        res = get_v16_premium_analysis(diag_t)
        if res:
            st.subheader(f"{res['light']} {diag_t} | 戰略評分: {res['score']}")
            
            # 專業 K 線圖繪製
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=res['df'].index, open=res['df']['Open'], high=res['df']['High'], low=res['df']['Low'], close=res['df']['Close'], name='K線'), row=1, col=1)
            fig.add_trace(go.Scatter(x=res['df'].index, y=res['df']['MA20'], line=dict(color='#E91E63', width=2), name='20MA(生命線)'), row=1, col=1)
            
            # 成交量配色
            colors = ['#26a69a' if res['df']['Close'].iloc[i] >= res['df']['Open'].iloc[i] else '#ef5350' for i in range(len(res['df']))]
            fig.add_trace(go.Bar(x=res['df'].index, y=res['df']['Volume'], marker_color=colors, name='成交量', opacity=0.8), row=2, col=1)
            
            fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False, margin=dict(t=30, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)
            
            send_v16_line(diag_t, res)
        else:
            st.error("查無資料或數據連線異常。台股請輸入代碼 (2330)，美股請確認代碼無誤 (NVDA, VOO)。")

# 戰略掃描區
st.markdown("---")
b1, b2, b3, b4 = st.columns(4)
def run_strategic_scan(stocks, mode):
    p = st.progress(0)
    for i, t in enumerate(stocks):
        r = get_v16_premium_analysis(t)
        if r and "🟢" in r['light']: send_v16_line(t, r)
        p.progress((i+1)/len(stocks))
        time.sleep(0.5)
    st.success(f"{mode} 戰略監控完成")

with b1:
    if st.button("📈 上市/ETF監控", use_container_width=True): run_strategic_scan(["0050","00830","2330","2317"], "上市ETF")
with b2:
    if st.button("🇺🇸 美股強勢監控", use_container_width=True): run_strategic_scan(["VOO","NVDA","TSLA","AAPL"], "美股強勢")
with b3:
    if st.button("💰 小資飆股偵測", use_container_width=True): run_strategic_scan(["2344","2409","2618","1605"], "小資飆股")
with b4:
    if st.button("🚀 上櫃飆股偵測", type="primary", use_container_width=True): run_strategic_scan(["8046","6142","3163","6125","5483"], "上櫃飆股")
