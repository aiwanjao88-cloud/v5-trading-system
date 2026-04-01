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

# --- 1. 核心參數與授權 ---
TOKEN = "p0hZsq9njQwsK2QYkeTQjYYyJ87MpttosPY8E7e6HIbJns3Ii2AnYj4Z+QNaGCVrDphhuFlGKHJCnfMleQ1XlCJj2FRu2UJTYj9dAZUFIZfB4SLcVjXncnsGLrpflCwc1O3bU4OotJqW3zeslTFk8QdB04t89/1O/w1cDnyilFU="
USER_ID = "Ud25e9519467182c8b844df5260bccde5"

# --- 2. 情報抓取引擎 (新聞標題) ---
def get_live_news(ticker_obj):
    try:
        news_data = ticker_obj.news[:3] # 僅取前 3 則關鍵新聞
        if not news_data: return "目前暫無即時相關新聞。"
        lines = []
        for n in news_data:
            title = n.get('title', '無標題')
            lines.append(f"▪️ {title}")
        return "\n".join(lines)
    except:
        return "無法獲取最新新聞摘要。"

# --- 3. 戰略數據引擎 (含紅綠燈、MA20/60、RSI) ---
def get_v135_stable_data(ticker):
    try:
        ticker = ticker.strip().upper()
        is_us = any(c.isalpha() for c in ticker)
        
        # 嘗試上市或上櫃後綴
        suffixes = ["", ".TW", ".TWO"] if not is_us else [""]
        tk_obj = None
        df = pd.DataFrame()
        
        for suf in suffixes:
            tk_obj = yf.Ticker(f"{ticker}{suf}")
            df = tk_obj.history(period="1y")
            if not df.empty: break
            
        if df.empty or len(df) < 60: return None
        
        # 數據清理
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df = df.astype(float)
        
        # 技術指標計算
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['MA60'] = ta.sma(df['Close'], length=60)
        macd = ta.macd(df['Close'])
        df['MACD'] = macd['MACD_12_26_9'] if macd is not None else 0
        df = df.dropna()
        
        now = df.iloc[-1]
        p, m5, m20 = now['Close'], now['MA5'], now['MA20']
        
        # 國發管理人加權評分
        score = 0
        if p > m5: score += 40
        if p > m20: score += 40
        if df['MACD'].iloc[-1] > 0: score += 20
        
        light = "🟢【建議進場】" if score >= 80 and p > m5 else ("🔴【絕對止損】" if p < m20 else "🟡【持有觀望】")
        news_text = get_live_news(tk_obj)
        mdj_url = f"https://www.moneydj.com/KMDJ/Search/SearchViewer.aspx?search={ticker}"
        
        return {
            "df": df.tail(100), "score": score, "light": light, "p": p, 
            "m5": m5, "m20": m20, "news": news_text, "mdj": mdj_url
        }
    except: return None

def send_full_report(ticker, res):
    msg = (
        f"🏛️ 國發 V13.5 戰略通報：{ticker}\n"
        f"狀態：{res['light']}\n"
        f"現價：{res['p']:.2f} | 評分：{res['score']}\n"
        f"------------------\n"
        f"✅ 進場參考：{res['m5']:.2f}\n"
        f"❌ 止損防線：{res['m20']:.2f}\n"
        f"------------------\n"
        f"📰 最新相關新聞：\n{res['news']}\n"
        f"🔗 MoneyDJ 情報：{res['mdj']}"
    )
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {TOKEN}"}
    payload = {"to":USER_ID, "messages":[{"type":"text", "text":msg}]}
    requests.post("https://api.line.me/v2/bot/message/push", headers=headers, data=json.dumps(payload), timeout=10)

# --- 4. 介面設計 ---
st.set_page_config(page_title="V13.5 國發戰略終端", layout="wide")
st.title("🛡️ 國發級投資終端 V13.5 (情報與進出防線整合)")

# 深度檢診區
c_in, c_btn = st.columns([3,1])
with c_in: diag_t = st.text_input("輸入台美股/ETF代碼 (如 2317, 00830, NVDA)", "00830").upper()
with c_btn:
    st.write("<br>", unsafe_allow_html=True)
    if st.button("🚀 執行深度戰略檢診", use_container_width=True):
        with st.spinner("情報數據同步中..."):
            res = get_v135_stable_data(diag_t)
            if res:
                st.subheader(f"{res['light']} {diag_t} | 評分: {res['score']}")
                st.info(f"📰 **最新即時新聞摘要：**\n{res['news']}")
                
                # TradingView 風格圖表
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
                fig.add_trace(go.Candlestick(x=res['df'].index, open=res['df']['Open'], high=res['df']['High'], low=res['df']['Low'], close=res['df']['Close'], name='K線'), row=1, col=1)
                fig.add_trace(go.Scatter(x=res['df'].index, y=res['df']['MA20'], line=dict(color='#E91E63', width=2), name='20MA'), row=1, col=1)
                fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
                
                send_full_report(diag_t, res)
            else: st.error("查無資料，請確認代碼格式是否正確。")

# 快速掃描按鈕
st.markdown("---")
b1, b2, b3, b4 = st.columns(4)
def run_strategic_scan(stocks, mode):
    p = st.progress(0)
    for i, t in enumerate(stocks):
        r = get_v135_stable_data(t)
        if r and "🟢" in r['light']: send_full_report(t, r)
        p.progress((i+1)/len(stocks))
        time.sleep(0.5)
    st.success(f"✅ {mode} 掃描完畢")

with b1:
    if st.button("📈 上市/ETF監控", use_container_width=True): run_strategic_scan(["00830","0050","00929","2330"], "波段")
with b2:
    if st.button("🇺🇸 美股強勢監控", use_container_width=True): run_strategic_scan(["NVDA","TSLA","PLTR","AAPL"], "美股")
with b3:
    if st.button("💰 小資飆股偵測", use_container_width=True): run_strategic_scan(["2344","2409","2618","1605"], "小資")
with b4:
    if st.button("🚀 上櫃飆股偵測", type="primary", use_container_width=True): run_strategic_scan(["8046","6142","3163","6125","5483"], "上櫃")
