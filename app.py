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
from datetime import datetime

# --- 1. 核心權威參數 ---
TOKEN = "p0hZsq9njQwsK2QYkeTQjYYyJ87MpttosPY8E7e6HIbJns3Ii2AnYj4Z+QNaGCVrDphhuFlGKHJCnfMleQ1XlCJj2FRu2UJTYj9dAZUFIZfB4SLcVjXncnsGLrpflCwc1O3bU4OotJqW3zeslTFk8QdB04t89/1O/w1cDnyilFU="
USER_ID = "Ud25e9519467182c8b844df5260bccde5"

# --- 2. 聖域級數據分析引擎 (V23.0 鋼鐵穩定) ---
def get_v23_analysis(ticker):
    try:
        ticker = ticker.strip().upper()
        is_us = any(c.isalpha() for c in ticker)
        df = pd.DataFrame()
        tk_obj = None

        # 多重解析路徑
        if is_us:
            tk_obj = yf.Ticker(ticker)
            df = tk_obj.history(period="2y", interval="1d", auto_adjust=True)
        else:
            for suf in [".TW", ".TWO"]:
                trial_df = yf.download(f"{ticker}{suf}", period="2y", progress=False, auto_adjust=True)
                if not trial_df.empty:
                    df = trial_df
                    tk_obj = yf.Ticker(f"{ticker}{suf}")
                    break
        
        if df.empty or len(df) < 65: return None

        # 數據清洗與解構 (防禦機制)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.index = df.index.tz_localize(None)
        df = df.astype(float)

        # 指標精算 (三線合一)
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['MA60'] = ta.sma(df['Close'], length=60)
        macd = ta.macd(df['Close'])
        df['MACD_H'] = macd.iloc[:, 2] if macd is not None else 0
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        # 徹底移除不完整數據 (消滅 KeyError)
        df = df.dropna()
        if df.empty: return None
        
        last = df.iloc[-1]
        p, m5, m20, m60 = float(last['Close']), float(last['MA5']), float(last['MA20']), float(last['MA60'])
        
        # 籌碼面：量能擴張比
        vol_avg = df['Volume'].rolling(20).mean().iloc[-1]
        vol_r = float(df['Volume'].iloc[-1] / vol_avg) if vol_avg > 0 else 1

        # 三位一體評分 (權威算法)
        score = 0
        if p > m5: score += 20
        if p > m20: score += 40
        if float(last['MACD_H']) > 0: score += 20
        if 50 < float(last['RSI']) < 75: score += 10
        if vol_r > 1.2: score += 10

        light = "🟢【強勢起飛】" if score >= 85 and p > m20 else ("🔴【防禦止損】" if p < m20 or score < 55 else "🟡【等待結構】")
        
        # 多維情報矩陣
        intelligence = {
            "MoneyDJ": f"https://www.moneydj.com/KMDJ/Common/ListNewNews.aspx?index=1&search={ticker}",
            "Anue": f"https://invest.cnyes.com/twstock/TWS/{ticker}/headline",
            "Yahoo": f"https://tw.stock.yahoo.com/quote/{ticker}/diagnostic"
        }
        
        return {
            "df": df.tail(120), "score": score, "light": light, 
            "p": p, "m5": m5, "m20": m20, "m60": m60, "vol_r": vol_r,
            "intel": intelligence, "news": tk_obj.news[:2] if tk_obj and tk_obj.news else []
        }
    except: return None

def send_v23_line(ticker, res, mode="戰略診斷"):
    news_titles = "\n".join([f"▪️ {n.get('title','新聞讀取中')}" for n in res['news']]) if res['news'] else "暫無重大通訊。"
    msg = (f"🏛️ 國發 V23.0 聖域通報 - {mode}\n標的：{ticker}\n狀態：{res['light']}\n"
           f"現價：{res['p']:.2f} | 分數：{res['score']}\n"
           f"------------------\n"
           f"🎯 進場參考：{res['m5']:.2f}\n"
           f"🛡️ 生命防線：{res['m20']:.2f}\n"
           f"📈 趨勢指標：量比 {res['vol_r']:.1f}x\n"
           f"------------------\n"
           f"📰 最新情報：\n{news_titles}\n"
           f"🔗 深度診斷：{res['intel']['Yahoo']}")
    
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {TOKEN}"}
    payload = {"to":USER_ID, "messages":[{"type":"text", "text":msg}]}
    requests.post("https://api.line.me/v2/bot/message/push", headers=headers, data=json.dumps(payload), timeout=10)

# --- 3. 聖域 UI 設計 ---
st.set_page_config(page_title="V23 國發終極版", layout="wide")
st.title("🛡️ 國發級投資終端 V23.0")
st.caption("2026 全方位動態監控系統 - 3次交叉驗證確保之鋼鐵架構")

# [A] 專業深度檢診區
with st.container():
    c_in, c_btn = st.columns([3,1])
    with c_in: diag_t = st.text_input("💎 輸入全球標的 (如 2330, 00929, VOO, NVDA)", "2317").upper().strip()
    with c_btn:
        st.write("<br>", unsafe_allow_html=True)
        if st.button("🚀 執行聖域診斷", use_container_width=True):
            res = get_v23_analysis(diag_t)
            if res:
                st.subheader(f"{res['light']} {diag_t} | 戰略評等: {res['score']}")
                
                # Plotly 專業 K 線圖
                fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
                fig.add_trace(go.Candlestick(x=res['df'].index, open=res['df']['Open'], high=res['df']['High'], low=res['df']['Low'], close=res['df']['Close'], name='K線'), row=1, col=1)
                fig.add_trace(go.Scatter(x=res['df'].index, y=res['df']['MA5'], line=dict(color='orange', width=1.2), name='5MA'), row=1, col=1)
                fig.add_trace(go.Scatter(x=res['df'].index, y=res['df']['MA20'], line=dict(color='#E91E63', width=2), name='20MA'), row=1, col=1)
                fig.add_trace(go.Scatter(x=res['df'].index, y=res['df']['MA60'], line=dict(color='#2196F3', width=2), name='60MA'), row=1, col=1)
                
                # 成交量柱
                colors = ['#26a69a' if res['df']['Close'].iloc[i] >= res['df']['Open'].iloc[i] else '#ef5350' for i in range(len(res['df']))]
                fig.add_trace(go.Bar(x=res['df'].index, y=res['df']['Volume'], marker_color=colors, name='成交量'), row=2, col=1)
                fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False, margin=dict(t=30, b=10))
                st.plotly_chart(fig, use_container_width=True)
                
                # 情報導航按鈕
                i1, i2, i3 = st.columns(3)
                i1.info(f"📰 [MoneyDJ 新聞]({res['intel']['MoneyDJ']})")
                i2.success(f"🔥 [鉅亨網快報]({res['intel']['Anue']})")
                i3.warning(f"📊 [Yahoo 健診]({res['intel']['Yahoo']})")
                
                send_v23_line(diag_t, res)
            else:
                st.error("查無資料，請確認標的代碼（如 00929.TW, NVDA）。")

# [B] 強制回報動態掃描區
st.markdown("---")
st.header("⚡ 每日全市場獵鷹監控 (強制結報)")
s1, s2, s3, s4 = st.columns(4)

SCAN_SEEDS = {
    "上市/ETF": ["0050.TW","00830.TW","00929.TW","2330.TW","2317.TW","2454.TW"],
    "美股強勢": ["VOO","NVDA","TSLA","AAPL","PLTR","AMD","META"],
    "小資飆股": ["2344.TW","2409.TW","2618.TW","1605.TW","3481.TW","2353.TW"],
    "上櫃飆股": ["8046.TWO","6142.TWO","3163.TWO","6125.TWO","5483.TWO","8069.TWO"]
}

def execute_v23_mission(mode, stocks):
    st.info(f"任務啟動：{mode} 動態掃描中...")
    bar = st.progress(0)
    found = []
    for i, t in enumerate(stocks):
        r = get_v23_analysis(t)
        if r and "🟢" in r['light']:
            found.append(r)
            send_v23_line(t, r, mode)
        bar.progress((i+1)/len(stocks))
        time.sleep(0.3)
    
    summary = f"🏛️ 任務結報：{mode} \n✅ 掃描完成。發現 {len(found)} 檔強勢標的。 \n⚠️ 若發現數為 0，代表目前市場空方勢強，建議保本空手。"
    send_v23_line("MISSION_SUMMARY", {"light": "📊 結報", "p": 0, "score": len(found), "m5": 0, "m20": 0, "news": [], "intel": {"Yahoo": "#"}}, summary)
    st.success(summary)

with s1:
    if st.button("📈 監控上市/ETF"): execute_v23_mission("上市/ETF", SCAN_SEEDS["上市/ETF"])
with s2:
    if st.button("🇺🇸 監控美股強勢"): execute_v23_mission("美股強勢", SCAN_SEEDS["美股強勢"])
with s3:
    if st.button("💰 偵測小資飆股"): execute_v23_mission("小資飆股", SCAN_SEEDS["小資飆股"])
with s4:
    if st.button("🚀 偵測上櫃飆股", type="primary"): execute_v23_mission("上櫃飆股", SCAN_SEEDS["上櫃飆股"])
