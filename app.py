import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import json

# --- 1. 固定設定區 (已填入您的專屬資訊) ---
FIXED_LINE_TOKEN = "p0hZsq9njQwsK2QYkeTQjYYyJ87MpttosPY8E7e6HIbJns3Ii2AnYj4Z+QNaGCVrDphhuFlGKHJCnfMleQ1XlCJj2FRu2UJTYj9dAZUFIZfB4SLcVjXncnsGLrpflCwc1O3bU4OotJqW3zeslTFk8QdB04t89/1O/w1cDnyilFU="
FIXED_USER_ID = "Ud25e9519467182c8b844df5260bccde5"

# --- 2. 核心邏輯函數 ---

def calculate_v5_score(df):
    """國發級波段評分邏輯 V6 - 5MA/20MA 強化版"""
    try:
        if len(df) < 30: return 0, None
        
        # 處理 yfinance 的多級索引
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # 技術指標計算
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
    """使用固定金鑰發送 LINE"""
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {FIXED_LINE_TOKEN}"
    }
    payload = {
        "to": FIXED_USER_ID,
        "messages": [{"type": "text", "text": message}]
    }
    try:
        requests.post(url, headers=headers, data=json.dumps(payload))
    except:
        pass

# --- 3. Streamlit 介面 ---

st.set_page_config(page_title="V6 國發級波段掃描器", layout="wide")
st.title("📈 V6 國發級波段掃描器 (全自動版)")

st.sidebar.header("🛠️ 系統狀態")
st.sidebar.success("✅ LINE 授權已自動載入")
st.sidebar.info(f"👤 接收者 ID: {FIXED_USER_ID[:10]}...")

# --- 4. 主程式執行區 ---

tickers = st.text_input("輸入監控股票代碼 (逗號分隔)", "2330,231
