import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import json

# --- 固定設定區 ---
FIXED_LINE_TOKEN = "p0hZsq9njQwsK2QYkeTQjYYyJ87MpttosPY8E7e6HIbJns3Ii2AnYj4Z+QNaGCVrDphhuFlGKHJCnfMleQ1XlCJj2FRu2UJTYj9dAZUFIZfB4SLcVjXncnsGLrpflCwc1O3bU4OotJqW3zeslTFk8QdB04t89/1O/w1cDnyilFU="
DEFAULT_USER_ID = "U0457d9036c0765c9287c975a6697072a" # 這是從您提供的截圖中辨識出的 ID

# --- 1. 核心邏輯函數 ---

def calculate_v5_score(df):
    """國發級波段評分邏輯 V6 - 5MA/20MA 強化版"""
    try:
        if len(df) < 30: return 0, None
        
        # 處理 yfinance 可能產生的多級索引
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
    except Exception as e:
        return 0, None

def send_line_message(token, user_id, message):
    """LINE Messaging API 推播函數"""
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    payload = {
        "to": user_id,
        "messages": [{"type": "text", "text": message}]
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        return response.status_code
    except:
        return None

# --- 2. Streamlit 介面與側邊欄 ---

st.set_page_config(page_title="V6 國發級波段掃描器", layout="wide")
st.title("📈 V6 國發級波段掃描器 (自動授權版)")

st.sidebar.header("🛠️ 系統狀態")
st.sidebar.success("✅ LINE Token 已固定載入")

# 允許手動覆蓋 User ID，若無輸入則用預設值
user_id_input = st.sidebar.text_input("您的 LINE User ID (留空則使用預設)", type="password")
final_user_id = user_id_input if user_id_input else DEFAULT_USER_ID

# 回測功能按鈕
st.sidebar.markdown("---")
if st.sidebar.button("📊 執行過去 30 天勝率回測"):
    st.sidebar.info("🔍 正在分析歷史訊號...")
    win_count = 0
    total_signals = 0
    test_tickers = ["2330", "2317", "2454", "2303", "2382", "3231", "2603"] 
    for t in test_tickers:
        df_hist = yf.download(f"{t}.TW", period="60d", progress=False)
        if len(df_hist) < 40: continue
        score_10d, _ = calculate_v5_score(df_hist.iloc[:-10])
        if score_10d >= 75:
            total_signals += 1
            if df_hist['Close'].iloc[-1] > df_hist['Close'].iloc[-10]:
                win_count += 1
    if total_signals > 0:
        st.sidebar.metric("波段模擬勝率", f"{(win_count/total_signals)*100:.1f}%", f"共 {total_signals} 次訊號")

# --- 3. 主程式執行區 ---

tickers = st.text_input("輸入監控股票代碼 (逗號分隔)", "2330,2317,2454,2303,2382,3231,2603")
ticker_list = [t.strip() for t in tickers.split(",")]

if st.button("🚀 開始掃描並同步發送 LINE"):
    results = [] 
    
    for ticker in ticker_list:
        data = yf.download(f"{ticker}.TW", period="8mo", progress=False)
        if data.empty:
            continue

        score, now = calculate_v5_score(data)
                
        if now is not None and not now.empty:
            now_price = float(now['Close'])
            ma5 = float(now['MA5'])
            ma20 = float(now['MA20'])
            stop_loss = now_price * 0.93
                    
            results.append({
                "代碼": ticker,
                "評分": score,
                "現價": round(now_price, 2),
                "5MA": round(ma5, 2),
                "20MA": round(ma20, 2),
                "停損參考": round(stop_loss, 2)
            })

            if score >= 75:
                is_above_ma5 = now_price > ma5
                level_tag = "🚨【特急·強勢標的】" if score >= 90 else "🚀【波段建議通知】"
                confirm_msg = "🟢 已站上 5MA，進場訊號確認。" if is_above_ma5 else "🟡 評分雖高但低於 5MA，建議等轉強。"
                
                msg = f"""{level_tag}
股票：{ticker}
評分：{score} 分
當前價格：{now_price:.2f}
{confirm_msg}
------------------
🛡️ 停損參考：{stop_loss:.2f}
⚓ 生命線(20MA)：{ma20:.2f}
💡 出場建議：收盤跌破 20MA
📊 線圖：https://tw.stock.yahoo.com/quote/{ticker}.TW"""
                
                send_line_message(FIXED_LINE_TOKEN, final_user_id, msg)

    if results:
        st.table(pd.DataFrame(results))
        st.success("掃描完成！訊息已自動發送。")
    else:
        st.warning("目前沒有符合評分門檻的股票。")
