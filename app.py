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

# --- 1. 機構級參數 ---
TOKEN = "p0hZsq9njQwsK2QYkeTQjYYyJ87MpttosPY8E7e6HIbJns3Ii2AnYj4Z+QNaGCVrDphhuFlGKHJCnfMleQ1XlCJj2FRu2UJTYj9dAZUFIZfB4SLcVjXncnsGLrpflCwc1O3bU4OotJqW3zeslTFk8QdB04t89/1O/w1cDnyilFU="
USER_ID = "Ud25e9519467182c8b844df5260bccde5"

# --- 2. 三位一體分析引擎 ---
def get_v15_tri_analysis(ticker):
    try:
        ticker = ticker.strip().upper()
        is_us = any(c.isalpha() for c in ticker)
        
        # A. 數據獲取 (對標 XQ/CMoney 數據清洗)
        full_t = ticker if is_us else f"{ticker}.TW"
        tk = yf.Ticker(full_t)
        df = tk.history(period="1y", auto_adjust=True)
        if df.empty and not is_us:
            full_t = f"{ticker}.TWO"
            tk = yf.Ticker(full_t)
            df = tk.history(period="1y", auto_adjust=True)
        
        if df.empty or len(df) < 60: return None
        df.index = df.index.tz_localize(None)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # B. 技術面 (MA + MACD + RSI)
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['MA60'] = ta.sma(df['Close'], length=60)
        macd = ta.macd(df['Close'])
        df['MACD_H'] = macd['MACDh_12_26_9']
        
        # C. 籌碼面評估 (成交量暴增率)
        avg_vol = df['Volume'].rolling(20).mean()
        vol_ratio = df['Volume'].iloc[-1] / avg_vol.iloc[-1]
        
        # D. 基本面概況 (透過 Info 獲取，對標財報狗)
        info = tk.info
        pe_ratio = info.get('forwardPE', 0)
        rev_growth = info.get('revenueGrowth', 0) * 100 # 營收成長率
        
        df = df.dropna()
        now = df.iloc[-1]
        p, m20 = now['Close'], now['MA20']
        
        # 三位一體評分
        score = 0
        if p > m20: score += 30                # 技術面：守住生命線
        if now['MACD_H'] > 0: score += 20     # 技術面：動能向上
        if vol_ratio > 1.2: score += 20        # 籌碼面：量增 (主力介入)
        if rev_growth > 0: score += 20         # 基本面：成長性
        if 0 < pe_ratio < 30: score += 10      # 基本面：估值合理
        
        light = "🟢【三面共振-大買】" if score >= 85 else ("🔴【防禦警示-減碼】" if p < m20 else "🟡【等待結構轉強】")
        
        # 官方工具連結
        mdj = f"https://www.moneydj.com/KMDJ/Search/SearchViewer.aspx?search={ticker}"
        y_select = f"https://tw.stock.yahoo.com/quote/{ticker}/diagnostic" # Yahoo 健檢
        
        return {
            "df": df.tail(100), "score": score, "light": light, "p": p, "m5": now['MA5'], "m20": m20, 
            "vol_r": vol_ratio, "rev_g": rev_growth, "pe": pe_ratio, "mdj": mdj, "y_s": y_select, "news": tk.news[:2]
        }
    except: return None

def send_v15_report(ticker, res):
    news_txt = "\n".join([f"▪️ {n['title']}" for n in res['news']])
    msg = (
        f"🏛️ 國發 V15 三位一體報告：{ticker}\n"
        f"級別：{res['light']}\n"
        f"現價：{res['p']:.2f} | 總分：{res['score']}\n"
        f"------------------\n"
        f"📊 技術：{'多頭排列' if res['score']>70 else '整理中'}\n"
        f"🔥 籌碼：量能放大 {res['vol_r']:.1f} 倍\n"
        f"💎 基本：營收成長 {res['rev_g']:.1f}%\n"
        f"------------------\n"
        f"✅ 進場參考：{res['m5']:.2f}\n"
        f"❌ 止損防線：{res['m20']:.2f}\n"
        f"------------------\n"
        f"📰 重點新聞：\n{news_txt}\n"
        f"🔗 Yahoo選股器：{res['y_s']}\n"
        f"🔗 MoneyDJ情報：{res['mdj']}"
    )
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {TOKEN}"}
    payload = {"to":USER_ID, "messages":[{"type":"text", "text":msg}]}
    requests.post("https://api.line.me/v2/bot/message/push", headers=headers, data=json.dumps(payload), timeout=10)

# --- 3. 介面設計 ---
st.set_page_config(page_title="V15 三位一體終端", layout="wide")
st.title("🛡️ 國發 V15：三位一體機構級選股終端")

# 專業選股工具推薦區 (Sidebar)
with st.sidebar:
    st.header("🛠️ 管理人推薦工具")
    st.markdown("1. **[財報狗](https://statementdog.com/)**：深挖基本面體質。")
    st.markdown("2. **[Yahoo 股市選股器](https://tw.stock.yahoo.com/screener/)**：多維度指標篩選。")
    st.markdown("3. **[XQ 策略選股](https://www.xq.com.tw/)**：專業量化腳本。")
    st.markdown("4. **[CMoney 籌碼K線](https://www.cmoney.tw/)**：追蹤主力分點。")

diag_t = st.text_input("🔍 輸入全球標的 (如 2330, 00830, NVDA)", "2317").upper()

if st.button("🚀 執行三位一體深度分析", use_container_width=True):
    res = get_v15_tri_analysis(diag_t)
    if res:
        st.subheader(f"{res['light']} {diag_t}")
        # 圖表
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=res['df'].index, open=res['df']['Open'], high=res['df']['High'], low=res['df']['Low'], close=res['df']['Close'], name='K線'), row=1, col=1)
        fig.add_trace(go.Scatter(x=res['df'].index, y=res['df']['MA20'], line=dict(color='#E91E63', width=2), name='20MA'), row=1, col=1)
        fig.add_trace(go.Bar(x=res['df'].index, y=res['df']['Volume'], name='成交量', opacity=0.5), row=2, col=1)
        fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
        send_v15_report(diag_t, res)
    else: st.error("查無資料，請確認代碼。")

# 戰略掃描區 (均內含三面評估)
st.markdown("---")
st.header("⚡ 戰略綠燈自動掃描 (三面共振版)")
b1, b2, b3, b4 = st.columns(4)
def run_v15_scan(stocks, mode):
    p = st.progress(0)
    for i, t in enumerate(stocks):
        r = get_v15_tri_analysis(t)
        if r and "🟢" in r['light']: send_v15_report(t, r)
        p.progress((i+1)/len(stocks))
        time.sleep(0.5)
    st.success(f"{mode} 監控完畢")

with b1:
    if st.button("📈 上市/ETF監控", use_container_width=True): run_v15_scan(["00830","0050","2330","2454"], "上市")
with b2:
    if st.button("🇺🇸 美股強勢監控", use_container_width=True): run_v15_scan(["NVDA","TSLA","PLTR","AAPL"], "美股")
with b3:
    if st.button("💰 小資飆股偵測", use_container_width=True): run_v15_scan(["2344","2409","2618","1605"], "小資")
with b4:
    if st.button("💎 上櫃飆股偵測", type="primary", use_container_width=True): run_v15_scan(["8046","6142","3163","6125","5483"], "上櫃")
