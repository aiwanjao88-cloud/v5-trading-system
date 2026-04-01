import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import requests
import json

# --- 1. 核心邏輯函數 ---

def calculate_v5_score(df):
    """國發級波段評分邏輯 V5"""
    try:
        if len(df) < 20: return 0, None
        
        # 技術指標計算
        df['EMA12'] = ta.ema(df['Close'], length=12)
        df['EMA26'] = ta.ema(df['Close'], length=26)
        macd = ta.macd(df['Close'])
        df['MACD'] = macd['MACD_12_26_9']
        df['RSI'] = ta.rsi(df['Close'], length=14)
        
        # 評分邏輯
        score = 0
        now = df.iloc[-1]
        
        if now['Close'] > now['EMA12']: score += 30
        if now['EMA12'] > now['EMA26']: score += 30
        if now['MACD'] > 0: score += 20
        if 50 < now['RSI'] < 70: score += 20
        
        return score, now
    except:
        return 0, None

def send_line_message(token, user_id, message):
    """LINE Messaging API 推播函數"""
    if not token or not user_id: return None
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

st.set_page_config(page_title="V5 國發級波段掃描器", layout="wide")
st.title("📈 V5 國發級波段掃描器")

st.sidebar.header("🛠️ 系統控制面板")
line_token = st.sidebar.text_input("LINE Channel Access Token", type="password")
line_user_id = st.sidebar.text_input("您的 LINE User ID", type="password")

# 回測功能按鈕
st.sidebar.markdown("---")
if st.sidebar.button("📊 執行過去 30 天勝率回測"):
    st.sidebar.info("🔍 正在分析歷史訊號...")
    win_count = 0
    total_signals = 0
    
    # 這裡使用的 tickers 會從下方定義的清單抓取
    test_tickers = ["2330", "2317", "2454", "2303", "2382", "3231", "2603"] 
    for t in test_tickers:
        df_hist = yf.download(f"{t}.TW", period="40d", progress=False)
        if len(df_hist) < 30: continue
        
        # 模擬 10 天前的情況
        score_10d, _ = calculate_v5_score(df_hist.iloc[:-10])
        if score_10d >= 75:
            total_signals += 1
            if df_hist['Close'].iloc[-1] > df_hist['Close'].iloc[-10]:
                win_count += 1
                
    if total_signals > 0:
        st.sidebar.metric("波段模擬勝率", f"{(win_count/total_signals)*100:.1f}%", f"共 {total_signals} 次訊號")
    else:
        st.sidebar.warning("近一個月無 75 分以上訊號")

# --- 3. 主程式執行區 ---

tickers = st.text_input("輸入監控股票代碼 (逗號分隔)", "2330,2317,2454,2303,2382,3231,2603")
ticker_list = [t.strip() for t in tickers.split(",")]

if st.button("🚀 開始掃描並同步發送 LINE"):
    results = []
    for ticker in ticker_list:
        data = yf.download(f"{ticker}.TW", period="6mo", progress=False)
        if data.empty: continue
        
        score, now = calculate_v5_score(data)
       if now is not None and not now.empty:
    now_price = now['Close']
else:
    st.error("暫時抓不到股票資料，請檢查網路或股票代碼是否正確。")
    st.stop() # 讓程式在這邊停住，不要往下跑出錯 now_price = now['Close']
        entry_price = now_price
        stop_loss = now_price * 0.93
        
        results.append({
            "代碼": ticker,
            "評分": score,
            "現價": round(now_price, 2),
            "進場參考": round(entry_price, 2),
            "停損參考": round(stop_loss, 2)
        })

        # --- 多重門檻發送邏輯 ---
        if score >= 75:
            # 決定警示等級
            if score >= 90:
                level_tag = "🚨【特急·強勢標的】"
                recommend = "🔥 動能極強，建議優先關注！"
            else:
                level_tag = "🚀【波段建議通知】"
                recommend = "✅ 趨勢確立，建議分批佈局。"

            # 生成圖表連結
            chart_url = f"https://tw.stock.yahoo.com/quote/{ticker}.TW"
            
            # 組合豐富版訊息
            msg = f"""{level_tag}
股票：{ticker}
評分：{score} 分
當前價格：{now_price:.2f}

{recommend}
------------------
🛡️ 停損參考：{stop_loss:.2f}
📊 即時線圖：{chart_url}"""
            
            send_line_message(line_token, line_user_id, msg)

    st.table(pd.DataFrame(results))
    st.success("掃描完成！高分標的已同步推播至 LINE。")
