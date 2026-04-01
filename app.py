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

# --- 2. 核心數據分析引擎 (修復 KeyError 與 美股相容性) ---
def get_v15_analysis(ticker):
    try:
        ticker = ticker.strip().upper()
        # 判定是否為美股：含有字母且不全是數字
        is_us = any(c.isalpha() for c in ticker)
        
        # 多重路徑抓取數據
        df = pd.DataFrame()
        tk = None
        
        if is_us:
            tk = yf.Ticker(ticker)
            df = tk.history(period="1y", interval="1d", auto_adjust=True)
        else:
            # 台股自動嘗試上市 (.TW) 或上櫃 (.TWO)
            for suffix in [".TW", ".TWO"]:
                temp_df = yf.download(f"{ticker}{suffix}", period="1y", progress=False, auto_adjust=True)
                if not temp_df.empty:
                    df = temp_df
                    tk = yf.Ticker(f"{ticker}{suffix}")
                    break

        if df.empty or len(df) < 60:
            return None

        # [關鍵修復] 移除時區並簡化欄位，防止技術指標計算報錯
        df.index = df.index.tz_localize(None)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.astype(float)

        # 指標計算
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['MA60'] = ta.sma(df['Close'], length=60)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        macd = ta.macd(df['Close'])
        # 防禦性抓取 MACD
        df['MACD_H'] = macd.iloc[:, 1] if macd is not None else 0
        
        # 籌碼面：量比
        vol_avg = df['Volume'].rolling(20).mean()
        vol_ratio = df['Volume'].iloc[-1] / vol_avg.iloc[-1] if vol_avg.iloc[-1] != 0 else 1

        # 基本面 (防禦性抓取 Info)
        try:
            info = tk.info
            rev_g = info.get('revenueGrowth', 0) * 100
        except:
            rev_g = 0

        # [關鍵修復] 確保計算後的最新數據沒有 NaN
        df_clean = df.dropna()
        if df_clean.empty: return None
        now = df_clean.iloc[-1]
        
        # 評分邏輯
        score = 0
        if now['Close'] > now['MA20']: score += 40
        if now['MACD_H'] > 0: score += 30
        if vol_ratio > 1.2: score += 20
        if rev_g > 0: score += 10
        
        light = "🟢【三面共振-大買】" if score >= 80 else ("🔴【絕對止損】" if now['Close'] < now['MA20'] else "🟡【區間盤整】")
        
        return {
            "df": df_clean.tail(100), "score": score, "light": light, 
            "p": now['Close'], "m5": now['MA5'], "m20": now['MA20'],
            "vol_r": vol_ratio, "rev_g": rev_g, "news": tk.news[:2]
        }
    except Exception as e:
        return None

def send_line_v15(ticker, res):
    news_txt = "\n".join([f"▪️ {n['title']}" for n in res['news']]) if res['news'] else "暫無重大新聞。"
    msg = (f"🏛️ V15.1 戰報：{ticker}\n級別：{res['light']}\n現價：{res['p']:.2f} | 分數：{res['score']}\n"
           f"------------------\n📊 技術：趨勢向上\n🔥 籌碼：量比 {res['vol_r']:.1f}\n💎 基本：營收增 {res['rev_g']:.1f}%\n"
           f"------------------\n✅ 進場:{res['m5']:.2f} | ❌ 止損:{res['m20']:.2f}\n"
           f"------------------\n📰 新聞：\n{news_txt}")
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {TOKEN}"}
    payload = {"to":USER_ID, "messages":[{"type":"text", "text":msg}]}
    requests.post("https://api.line.me/v2/bot/message/push", headers=headers, data=json.dumps(payload), timeout=10)

# --- 3. 介面與顯示 ---
st.set_page_config(page_title="V15.1 穩定防禦版", layout="wide")
st.title("🛡️ 國發 V15.1：三位一體穩定防禦終端")

# 側邊欄工具
with st.sidebar:
    st.header("🛠️ 管理人推薦")
    st.markdown("1. [財報狗](https://statementdog.com/)\n2. [Yahoo選股器](https://tw.stock.yahoo.com/screener/)\n3. [MoneyDJ](https://www.moneydj.com/)")

diag_t = st.text_input("🔍 輸入全球標的 (例: 2330, VOO, NVDA)", "2317").upper()

if st.button("🚀 執行三位一體分析", use_container_width=True):
    with st.spinner("數據同步與指標計算中..."):
        res = get_v15_analysis(diag_t)
        if res:
            st.subheader(f"{res['light']} {diag_t} 分數: {res['score']}")
            # 專業K線圖
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
            fig.add_trace(go.Candlestick(x=res['df'].index, open=res['df']['Open'], high=res['df']['High'], low=res['df']['Low'], close=res['df']['Close'], name='K線'), row=1, col=1)
            fig.add_trace(go.Scatter(x=res['df'].index, y=res['df']['MA20'], line=dict(color='#E91E63', width=2), name='20MA'), row=1, col=1)
            fig.add_trace(go.Bar(x=res['df'].index, y=res['df']['Volume'], name='量', opacity=0.5), row=2, col=1)
            fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
            send_line_v15(diag_t, res)
        else:
            st.error("查無資料或數據源超時，請檢查代碼（美股如 VOO, 台股如 2330）。")

# 自動監控
st.markdown("---")
b1, b2, b3, b4 = st.columns(4)
def run_scan(stocks, mode):
    p = st.progress(0)
    for i, t in enumerate(stocks):
        r = get_v15_analysis(t)
        if r and "🟢" in r['light']: send_line_v15(t, r)
        p.progress((i+1)/len(stocks))
        time.sleep(0.5)
    st.success(f"{mode} 掃描完畢")

with b1:
    if st.button("📈 上市/ETF監控", use_container_width=True): run_scan(["0050","00830","2330","2454"], "上市")
with b2:
    if st.button("🇺🇸 美股強勢監控", use_container_width=True): run_scan(["VOO","NVDA","TSLA","AAPL"], "美股")
with b3:
    if st.button("💰 小資飆股偵測", use_container_width=True): run_scan(["2344","2409","2618","1605"], "小資")
with b4:
    if st.button("🚀 上櫃飆股偵測", type="primary", use_container_width=True): run_scan(["8046","6142","3163","6125","5483"], "上櫃")
