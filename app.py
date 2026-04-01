import streamlit as st
import yfinance as yf
import pandas_ta as ta
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- 1. 初始設定與 Line 通知函式 ---
st.set_page_config(page_title="V5 專業多選股系統", layout="wide")

def send_line_notification(token, message):
    """發送 Line Notify 通知"""
    url = "https://notify-api.line.me/api/notify"
    headers = {"Authorization": f"Bearer {token}"}
    data = {"message": message}
    try:
        response = requests.post(url, headers=headers, data=data)
        return response.status_code
    except:
        return None

# --- 2. 側邊欄配置 ---
st.sidebar.header("🛠️ 系統控制面板")
line_token = st.sidebar.text_input("Line Notify Token", type="password", help="請至 Line Notify 官網申請")
watch_list = st.sidebar.multiselect(
    "監控清單", 
    ["2330", "2317", "2454", "2303", "2603", "1513", "2382", "3231"],
    default=["2330", "2317", "2454"]
)
custom_stock = st.sidebar.text_input("新增代碼 (如: 2881)")
if custom_stock:
    watch_list.append(custom_stock)

# --- 3. 核心運算引擎 ---
@st.cache_data(ttl=3600)
def analyze_stock(symbol):
    try:
        full_symbol = f"{symbol}.TW"
        df = yf.download(full_symbol, start=(datetime.now() - timedelta(days=200)), progress=False)
        if df.empty or len(df) < 100: return None
        
        if df.columns.nlevels > 1: df.columns = df.columns.get_level_values(0)
        
        # 指標計算
        df['MA100'] = ta.sma(df['Close'], length=100)
        df['VMA20'] = ta.sma(df['Volume'], length=20)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        now = df.iloc[-1]
        prev = df.iloc[-2]
        high_60 = df['High'].iloc[-61:-1].max()
        
        # 評分邏輯
        c1 = now['Close'] > now['MA100']
        c2 = now['MA100'] > df['MA100'].iloc[-5]
        c3 = now['Close'] >= high_60
        c4 = now['Volume'] > now['VMA20'] * 1.5
        
        score = sum([c1, c2, c3, c4]) * 25
        
        return {
            "代碼": symbol,
            "價格": round(float(now['Close']), 2),
            "漲跌": f"{((now['Close']-prev['Close'])/prev['Close']*100):.2f}%",
            "評分": int(score),
            "信號": "🚀 強力噴發" if score >= 75 else "⚖️ 觀察",
            "建議進場": round(float(now['Close']), 1),
            "停損參考": round(float(now['Close'] - 2*now['ATR']), 1)
        }
    except:
        return None

# --- 4. 主介面展示 ---
st.title("🛡️ V5 國發級波段掃描器")

results = []
for s in watch_list:
    res = analyze_stock(s)
    if res: results.append(res)

if results:
    res_df = pd.DataFrame(results)
    
    # 亮點顯示：高分標的
    high_score_stocks = res_df[res_df['評分'] >= 75]
    
    st.subheader("📊 即時掃描結果")
    st.dataframe(res_df.style.highlight_max(subset=['評分'], color='#2E7D32'), use_container_width=True)

    # --- 5. 自動通知邏輯 ---
    st.divider()
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.write("### 🤖 自動化動作")
        if not high_score_stocks.empty:
            if st.button("發送高分標的至 Line"):
                if line_token:
                    msg = "\n🔥 V5 系統選股觸發！\n"
                    for _, row in high_score_stocks.iterrows():
                        msg += f"\n📈 {row['代碼']} | 評分: {row['評分']}\n價格: {row['價格']}\n建議: {row['建議進場']}\n停損: {row['停損參考']}\n"
                    
                    status = send_line_notification(line_token, msg)
                    if status == 200:
                        st.success("通知已成功發送！")
                    else:
                        st.error("發送失敗，請檢查 Token。")
                else:
                    st.warning("請先在左側輸入 Line Token。")
        else:
            st.info("目前無符合 75 分標的，暫無通知。")

    with col2:
        st.write("### 📝 策略說明")
        with st.expander("查看評分標準"):
            st.write("""
            1. **週線站穩** (25分)：價格在 100MA 之上。
            2. **趨勢向上** (25分)：100MA 角度為正。
            3. **壓力突破** (25分)：突破過去 60 日高點。
            4. **動能爆發** (25分)：成交量大於均量 1.5 倍。
            """)

else:
    st.warning("請在左側選單加入監控代碼。")