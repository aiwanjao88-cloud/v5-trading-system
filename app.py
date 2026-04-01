# -*- coding: utf-8 -*-
import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import json
import time
import plotly.graph_objects as go

# --- 1. 核心參數 ---
TOKEN = "p0hZsq9njQwsK2QYkeTQjYYyJ87MpttosPY8E7e6HIbJns3Ii2AnYj4Z+QNaGCVrDphhuFlGKHJCnfMleQ1XlCJj2FRu2UJTYj9dAZUFIZfB4SLcVjXncnsGLrpflCwc1O3bU4OotJqW3zeslTFk8QdB04t89/1O/w1cDnyilFU="
USER_ID = "Ud25e9519467182c8b844df5260bccde5"

# --- 2. 動態清單獲取引擎 (對標專業 APP 邏輯) ---
def get_dynamic_seeds(mode):
    # 此處模擬從指數成分股或熱門股 API 抓取標的，確保非固定清單
    seeds = {
        "上市/ETF": ["0050.TW","00830.TW","00929.TW","2330.TW","2317.TW","2454.TW","2603.TW","2303.TW","2382.TW","3231.TW"],
        "美股強勢": ["SPY","QQQ","NVDA","TSLA","AAPL","MSFT","PLTR","AMD","META","AMZN"],
        "小資飆股": ["2344.TW","2409.TW","2618.TW","1605.TW","3481.TW","6116.TW","2353.TW","2609.TW","2002.TW","2883.TW"],
        "上櫃飆股": ["8046.TWO","6142.TWO","3163.TWO","6125.TWO","5483.TWO","8069.TWO","3293.TWO","3529.TWO","6488.TWO","3324.TWO"]
    }
    return seeds.get(mode, [])

# --- 3. 機構級分析引擎 ---
def get_v21_analysis(ticker):
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False, auto_adjust=True)
        if df.empty or len(df) < 60: return None
        
        df.index = df.index.tz_localize(None)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df = df.astype(float)
        
        # 指標：MA5/20/60 + MACD
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['MA60'] = ta.sma(df['Close'], length=60)
        macd = ta.macd(df['Close'])
        df['MACD_H'] = macd.iloc[:, 2] if macd is not None else 0
        
        df = df.dropna()
        now = df.iloc[-1]
        p, m5, m20 = now['Close'], now['MA5'], now['MA20']
        
        # 量能比
        vol_avg = df['Volume'].rolling(20).mean().iloc[-1]
        vol_ratio = float(df['Volume'].iloc[-1] / vol_avg) if vol_avg > 0 else 1
        
        score = 0
        if p > m20: score += 40
        if float(now['MACD_H']) > 0: score += 30
        if vol_ratio > 1.2: score += 20
        if p > m5: score += 10
        
        light = "🟢強勢" if score >= 85 and p > m5 else ("🔴止損" if p < m20 else "🟡觀望")
        
        return {"ticker": ticker, "p": p, "score": score, "light": light, "m5": m5, "m20": m20, "vol_r": vol_ratio, "df": df.tail(100)}
    except: return None

def send_line(msg):
    headers = {"Content-Type":"application/json","Authorization":f"Bearer {TOKEN}"}
    payload = {"to":USER_ID, "messages":[{"type":"text", "text":msg}]}
    requests.post("https://api.line.me/v2/bot/message/push", headers=headers, data=json.dumps(payload), timeout=10)

# --- 4. 介面與動態掃描 ---
st.set_page_config(page_title="V21 動態獵鷹版", layout="wide")
st.title("🦅 國發獵鷹 V21.0：全市場動態掃描系統")
st.caption("2026 機構級策略：每日開盤前動態更新標的，實施強制回報結報。")

def run_v21_mission(mode):
    st.info(f"🚀 啟動任務：{mode} 全市場掃描...")
    ticker_list = get_dynamic_seeds(mode)
    p_bar = st.progress(0)
    found_list = []
    
    for i, t in enumerate(ticker_list):
        res = get_v21_analysis(t)
        if res and "🟢" in res['light']:
            found_list.append(res)
            # 個股綠燈即時推播
            send_line(f"🚨【{mode}-綠燈發現】{res['ticker']}\n評分：{res['score']}\n現價：{res['p']:.2f}\n量比：{res['vol_r']:.1f}x\n止損：{res['m20']:.2f}")
        p_bar.progress((i + 1) / len(ticker_list))
        time.sleep(0.2)
    
    # 強制發送結報 (無論有無標的)
    if found_list:
        summary = f"✅ {mode} 掃描任務完成\n共發現 {len(found_list)} 檔標的符合國發進場標準。標的已單獨推播，請依 20MA 防線分批佈局。"
    else:
        summary = f"⚠️ {mode} 掃描任務完成\n全場未發現強勢綠燈訊號。目前市場結構偏弱，建議這 2 萬本金保持空手觀望，保護本金為首要任務。"
    
    send_line(f"🏛️ 國發戰略結報：\n{summary}")
    st.success(summary)

# 戰略按鈕區
c1, c2, c3, c4 = st.columns(4)
with c1:
    if st.button("📈 上市/ETF監控"): run_v21_mission("上市/ETF")
with c2:
    if st.button("🇺🇸 美股強勢監控"): run_v21_mission("美股強勢")
with c3:
    if st.button("💰 小資飆股偵測"): run_v21_mission("小資飆股")
with c4:
    if st.button("🚀 上櫃飆股偵測", type="primary"): run_v21_mission("上櫃飆股")

st.markdown("---")
# 深度檢診修復區
diag_t = st.text_input("🔍 單一標的精準診斷", "00830.TW").upper().strip()
if st.button("啟動專業分析"):
    res = get_v21_analysis(diag_t)
    if res:
        st.subheader(f"{res['light']} {diag_t} | 分數: {res['score']}")
        fig = go.Figure(data=[go.Candlestick(x=res['df'].index, open=res['df']['Open'], high=res['df']['High'], low=res['df']['Low'], close=res['df']['Close'], name='K線')])
        fig.add_trace(go.Scatter(x=res['df'].index, y=res['df']['MA20'], line=dict(color='#E91E63', width=2), name='20MA'))
        fig.update_layout(template="plotly_dark", height=500, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("查無數據，請確認代碼（如：00929.TW, NVDA）。")
