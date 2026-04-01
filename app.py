# -*- coding: utf-8 -*-
import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import json
import time

# --- 1. 固定設定區 ---
FIXED_LINE_TOKEN = "p0hZsq9njQwsK2QYkeTQjYYyJ87MpttosPY8E7e6HIbJns3Ii2AnYj4Z+QNaGCVrDphhuFlGKHJCnfMleQ1XlCJj2FRu2UJTYj9dAZUFIZfB4SLcVjXncnsGLrpflCwc1O3bU4OotJqW3zeslTFk8QdB04t89/1O/w1cDnyilFU="
FIXED_USER_ID = "Ud25e9519467182c8b844df5260bccde5"

# --- 2. 核心邏輯函數 ---

def calculate_v5_score(df):
    try:
        if len(df) < 30: return 0, None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df['EMA12'] = ta.ema(df['Close'], length=12)
        df['EMA26'] = ta.ema(df['Close'], length=26)
        df['MA5'] = ta.sma(df['Close'], length=5)    
        df['MA20'] = ta.sma(df['Close'], length=20)  
        
        macd = ta.macd(df['Close'])
        df['MACD'] = macd['MACD_12_26_9']
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        score = 0
        now = df.iloc[-1]
        
        if now['Close'] > now['EMA12']: score += 30
        if now['EMA12'] > now['EMA26']: score += 30
        if now['MACD'] > 0: score += 20
        if 50 < now['RSI'] < 70: score += 20
        
        return score, now
    except:
        return 0, None

def send_line_message(message):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {FIXED_LINE_TOKEN}"}
    payload = {"to": FIXED_USER_ID, "messages": [{"type": "text", "text": message}]}
    try:
        requests.post(url, headers=headers, data=json.dumps(payload), timeout=10)
    except:
        pass

# --- 3. 介面設計 ---

st.set_page_config(page_title="V7 國發級全台股掃描器", layout="wide")
st.title("📈 V7 國發級全台股掃描器")

st.sidebar.header("🛠️ 系統狀態")
st.sidebar.success("✅ LINE 授權已自動載入")

# 這裡預設放幾百檔具代表性的上市標的，避免全掃描 1800 檔導致被鎖 IP
# 如果你想掃描「真正的全部」，可以搜尋 '台股所有代碼清單' 貼進來
ALL_TW_STOCKS = ["2330","2317","2454","2303","2382","3231","2603","2609","2615","2618","2610","2357","2353","2324","2301","2376","2377","2408","2409","3481","3037","3034","2379","6239","2881","2882","2886","2891","2884","2885","5880","2892","2880","2883","2887","2890","1101","1102","1301","1303","1326","6505","2005","2105","2201","2207","2912","5903","9904","9910"]

# --- 4. 掃描執行邏輯 ---

def run_scanner(target_list, is_full_scan=False):
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total = len(target_list)
    for i, ticker in enumerate(target_list):
        status_text.text(f"正在掃描 ({i+1}/{total}): {ticker}")
        progress_bar.progress((i + 1) / total)
        
        data = yf.download(f"{ticker}.TW", period="8mo", progress=False)
        if data.empty: continue

        score, now = calculate_v5_score(data)
        if now is not None and score >= 75:
            now_price = float(now['Close'])
            ma5 = float(now['MA5'])
            ma20 = float(now['MA20'])
            
            # 只有站上 5MA 的才傳送 LINE，過濾噪音
            if now_price > ma5:
                res = {
                    "代碼": ticker,
                    "評分": score,
                    "現價": round(now_price, 2),
                    "20MA": round(ma20, 2)
                }
                results.append(res)
                
                msg = f"🚨【全域掃描發現】\n股票：{ticker}\n評分：{score}\n價格：{now_price:.2f}\n------------------\n⚓ 生命線(20MA)：{ma20:.2f}\n💡 建議：趨勢強勁且站上5MA"
                send_line_message(msg)
        
        # 稍微停頓，避免被 yfinance 封鎖
        if is_full_scan: time.sleep(0.1)
            
    return results

# --- 5. 主程式按鈕 ---

col1, col2 = st.columns(2)

with col1:
    user_input = st.text_input("自選監控清單", "2330,2317,2454,2603")
    if st.button("🚀 掃描自選清單"):
        list_to_scan = [t.strip() for t in user_input.split(",") if t.strip()]
        final_res = run_scanner(list_to_scan)
        if final_res:
            st.table(pd.DataFrame(final_res))
        else:
            st.warning("自選清單中無 75 分以上標的。")

with col2:
    st.write("掃描預設熱門權值股 (約 50 檔)")
    if st.button("🔍 啟動全台股大數據掃描"):
        with st.spinner("大數據分析中...請稍候..."):
            final_res = run_scanner(ALL_TW_STOCKS, is_full_scan=True)
            if final_res:
                st.success(f"掃描完成！共發現 {len(final_res)} 檔強勢標的。")
                st.table(pd.DataFrame(final_res))
            else:
                st.warning("目前市場無符合高分標的。")
