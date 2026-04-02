# -*- coding: utf-8 -*-
"""
V33.1 國泰手動下單面板版
--------------------------------
安裝：
pip install streamlit yfinance pandas pandas_ta requests

執行：
streamlit run app_v331_cathay_manual.py

設定 LINE（擇一）：
1) .streamlit/secrets.toml
   LINE_TOKEN = "p0hZsq9njQwsK2QYkeTQjYYyJ87MpttosPY8E7e6HIbJns3Ii2AnYj4Z+QNaGCVrDphhuFlGKHJCnfMleQ1XlCJj2FRu2UJTYj9dAZUFIZfB4SLcVjXncnsGLrpflCwc1O3bU4OotJqW3zeslTFk8QdB04t89/1O/w1cDnyilFU="
   LINE_USER_ID = "Ud25e9519467182c8b844df5260bccde5"

2) 環境變數
   LINE_TOKEN=...
   LINE_USER_ID=...
"""

import os
import json
from datetime import datetime
from typing import Optional, Tuple

import requests
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import streamlit as st


# =========================
# 基本設定
# =========================
APP_TITLE = "V33.1 國泰手動下單面板"
STATE_FILE = "v331_manual_state.json"
ORDERS_FILE = "v331_manual_orders.csv"
LOG_FILE = "v331_scan_log.csv"

DEFAULT_WATCHLIST = "2330,2317,2454,2603,2344,NVDA,TSLA,AMD,PLTR,QQQM,VOO,SMH,TSM,SCHD"
TW_MARKET_INDEX = "^TWII"
US_MARKET_INDEX = "^GSPC"
BASE_CAPITAL = 100000
RISK_PER_TRADE = 0.01
MAX_POSITION_PCT = 0.20
MIN_HISTORY = 120
SIDEWAYS_RANGE_PCT = 8.0
SIDEWAYS_ATR_PCT = 3.0
BUY_SCORE_THRESHOLD = 85
REDUCE_SCORE_THRESHOLD = 70


# =========================
# 安全讀取 LINE 設定
# =========================
def get_secret(name: str, default: str = "") -> str:
    try:
        if name in st.secrets:
            return str(st.secrets[name]).strip()
    except Exception:
        pass
    return os.getenv(name, default).strip()


LINE_TOKEN = get_secret("LINE_TOKEN")
LINE_USER_ID = get_secret("LINE_USER_ID")
ENABLE_LINE = bool(LINE_TOKEN and LINE_USER_ID)


# =========================
# 工具函式
# =========================
def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def safe_float(x, default=0.0) -> float:
    try:
        if x is None or pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default


def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    out = df.copy()
    if isinstance(out.columns, pd.MultiIndex):
        out.columns = out.columns.get_level_values(0)

    out.index = pd.to_datetime(out.index)
    try:
        out.index = out.index.tz_localize(None)
    except Exception:
        pass

    return out.dropna(how="all")


def detect_market(symbol: str) -> bool:
    symbol = symbol.strip().upper()
    return any(c.isalpha() for c in symbol)  # True = 美股 / 英文代碼


def load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {"positions": {}, "last_scan": [], "last_orders": []}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"positions": {}, "last_scan": [], "last_orders": []}


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def append_csv(path: str, row: dict) -> None:
    df = pd.DataFrame([row])
    if os.path.exists(path):
        df.to_csv(path, mode="a", header=False, index=False, encoding="utf-8-sig")
    else:
        df.to_csv(path, mode="w", header=True, index=False, encoding="utf-8-sig")


def push_line(text: str) -> tuple[bool, str]:
    if not ENABLE_LINE:
        return False, "未設定 LINE_TOKEN / LINE_USER_ID"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_TOKEN}",
    }
    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": text}]
    }

    try:
        r = requests.post(
            "https://api.line.me/v2/bot/message/push",
            headers=headers,
            data=json.dumps(payload),
            timeout=10
        )
        if 200 <= r.status_code < 300:
            return True, f"LINE 推播成功 ({r.status_code})"
        return False, f"LINE 推播失敗 ({r.status_code}) {r.text[:200]}"
    except Exception as e:
        return False, f"LINE 例外：{e}"


# =========================
# 資料與技術指標
# =========================
def get_symbol_data(symbol: str, period: str = "1y") -> Tuple[pd.DataFrame, str, bool]:
    symbol = symbol.strip().upper()
    is_us = detect_market(symbol)

    if is_us:
        tk = yf.Ticker(symbol)
        df = tk.history(period=period, auto_adjust=True)
        df = normalize_df(df)
        chart_url = f"https://www.tradingview.com/symbols/{symbol}/"
        return df, chart_url, True

    for suf in [".TW", ".TWO"]:
        full = f"{symbol}{suf}"
        df = yf.download(full, period=period, progress=False, auto_adjust=True)
        df = normalize_df(df)
        if not df.empty:
            chart_url = f"https://tw.stock.yahoo.com/quote/{symbol}/chart"
            return df, chart_url, False

    return pd.DataFrame(), "", False


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["MA5"] = ta.sma(out["Close"], length=5)
    out["MA20"] = ta.sma(out["Close"], length=20)
    out["MA60"] = ta.sma(out["Close"], length=60)

    macd = ta.macd(out["Close"], fast=12, slow=26, signal=9)
    if macd is not None and not macd.empty:
        out["MACD"] = macd.iloc[:, 0]
        out["MACD_SIGNAL"] = macd.iloc[:, 1]
        out["MACD_H"] = macd.iloc[:, 2]
    else:
        out["MACD"] = 0.0
        out["MACD_SIGNAL"] = 0.0
        out["MACD_H"] = 0.0

    out["VOL_MA20"] = ta.sma(out["Volume"], length=20)
    out["ATR14"] = ta.atr(out["High"], out["Low"], out["Close"], length=14)
    out["ATR_PCT"] = (out["ATR14"] / out["Close"]) * 100
    out["HH20"] = out["High"].rolling(20).max()
    out["LL20"] = out["Low"].rolling(20).min()
    out["RET_5D"] = out["Close"].pct_change(5) * 100
    return out.dropna().copy()


def get_market_filter(is_us: bool) -> dict:
    index_symbol = US_MARKET_INDEX if is_us else TW_MARKET_INDEX
    mdf = yf.download(index_symbol, period="1y", progress=False, auto_adjust=True)
    mdf = normalize_df(mdf)

    if mdf.empty or len(mdf) < 60:
        return {
            "market_symbol": index_symbol,
            "market_ok": False,
            "index_price": None,
            "index_ma20": None,
            "index_ma60": None,
            "market_trend": "N/A"
        }

    if isinstance(mdf.columns, pd.MultiIndex):
        mdf.columns = mdf.columns.get_level_values(0)

    mdf["MA20"] = ta.sma(mdf["Close"], length=20)
    mdf["MA60"] = ta.sma(mdf["Close"], length=60)
    mdf = mdf.dropna()

    now = mdf.iloc[-1]
    price = safe_float(now["Close"])
    ma20 = safe_float(now["MA20"])
    ma60 = safe_float(now["MA60"])

    market_ok = price > ma20 and ma20 >= ma60
    market_trend = "🟢多頭允許做多" if market_ok else "🔴大盤不允許擴張部位"

    return {
        "market_symbol": index_symbol,
        "market_ok": market_ok,
        "index_price": price,
        "index_ma20": ma20,
        "index_ma60": ma60,
        "market_trend": market_trend
    }


# =========================
# V33.1 引擎
# =========================
def calc_engine(symbol: str) -> Optional[dict]:
    try:
        raw_df, chart_url, is_us = get_symbol_data(symbol, period="1y")
        if raw_df.empty or len(raw_df) < MIN_HISTORY:
            return None

        df = add_indicators(raw_df)
        if df.empty or len(df) < 60:
            return None

        now = df.iloc[-1]
        p = safe_float(now["Close"])
        m5 = safe_float(now["MA5"])
        m20 = safe_float(now["MA20"])
        m60 = safe_float(now["MA60"])
        macd_h = safe_float(now["MACD_H"])
        vol = safe_float(now["Volume"])
        vol_ma20 = safe_float(now["VOL_MA20"])
        atr_pct = safe_float(now["ATR_PCT"])
        hh20 = safe_float(now["HH20"])
        ll20 = safe_float(now["LL20"])
        ret_5d = safe_float(now["RET_5D"])

        market = get_market_filter(is_us)
        market_ok = market["market_ok"]

        range_pct = ((hh20 - ll20) / ll20 * 100) if ll20 > 0 else 0.0
        sideways = (range_pct < SIDEWAYS_RANGE_PCT) and (atr_pct < SIDEWAYS_ATR_PCT)

        breakout = p >= hh20 * 0.995
        valid_breakout = breakout and (vol > vol_ma20 * 1.2)
        near_ma20 = abs(p - m20) / m20 <= 0.03 if m20 > 0 else False

        score = 0
        if p > m5:
            score += 15
        if p > m20:
            score += 25
        if m20 > m60:
            score += 20
        if macd_h > 0:
            score += 15
        if market_ok:
            score += 15
        if valid_breakout:
            score += 10

        if p < m20:
            status = "🔴止損"
        elif sideways:
            status = "🟡盤整停手"
        elif score >= BUY_SCORE_THRESHOLD and p > m20:
            status = "🟢強勢"
        else:
            status = "🟡觀望"

        signals = []
        if (
            score >= BUY_SCORE_THRESHOLD and
            p > m20 and
            m20 > m60 and
            macd_h > 0 and
            market_ok and
            not sideways and
            (near_ma20 or valid_breakout)
        ):
            signals.append("BUY")

        if p < m20:
            signals.append("SELL")

        if score < REDUCE_SCORE_THRESHOLD and p > m20:
            signals.append("REDUCE")

        if (not market_ok) and p > m20 and score >= REDUCE_SCORE_THRESHOLD:
            if "REDUCE" not in signals and "SELL" not in signals:
                signals.append("REDUCE")

        stop_loss_price = min(m20, p * 0.92)
        take_profit_1 = p * 1.08
        take_profit_2 = p * 1.12

        if p < m20:
            risk_tag = "⚠️跌破生命線"
        elif sideways:
            risk_tag = "⛔盤整"
        else:
            risk_tag = "✅安全"

        return {
            "ticker": symbol.strip().upper(),
            "is_us": is_us,
            "price": p,
            "m5": m5,
            "m20": m20,
            "m60": m60,
            "macd_h": macd_h,
            "vol": vol,
            "vol_ma20": vol_ma20,
            "atr_pct": atr_pct,
            "range_pct": range_pct,
            "ret_5d": ret_5d,
            "score": score,
            "status": status,
            "signals": signals,
            "valid_breakout": valid_breakout,
            "near_ma20": near_ma20,
            "market_ok": market_ok,
            "market_trend": market["market_trend"],
            "market_symbol": market["market_symbol"],
            "index_price": market["index_price"],
            "index_ma20": market["index_ma20"],
            "index_ma60": market["index_ma60"],
            "stop_loss_price": stop_loss_price,
            "take_profit_1": take_profit_1,
            "take_profit_2": take_profit_2,
            "risk_tag": risk_tag,
            "chart_url": chart_url,
        }

    except Exception:
        return None


# =========================
# 部位 / 單據
# =========================
def calc_position_size(entry_price: float, stop_price: float) -> tuple[int, float]:
    if entry_price <= 0 or stop_price <= 0 or entry_price <= stop_price:
        return 0, 0.0

    risk_budget = BASE_CAPITAL * RISK_PER_TRADE
    per_share_risk = entry_price - stop_price
    qty = int(risk_budget / per_share_risk)

    max_capital_per_trade = BASE_CAPITAL * MAX_POSITION_PCT
    max_qty_by_capital = int(max_capital_per_trade / entry_price)
    qty = min(qty, max_qty_by_capital)
    qty = max(qty, 0)

    return qty, qty * entry_price


def build_order_ticket(res: dict, signal: str, positions: dict) -> Optional[dict]:
    symbol = res["ticker"]
    price = res["price"]
    stop_price = res["stop_loss_price"]

    pos = positions.get(symbol, {"qty": 0, "avg_price": 0})
    cur_qty = int(pos.get("qty", 0))

    if signal == "BUY":
        qty, amount = calc_position_size(price, stop_price)
        if qty <= 0:
            return None
        return {
            "timestamp": now_str(),
            "ticker": symbol,
            "signal": "BUY",
            "side": "BUY",
            "price": round(price, 4),
            "qty": qty,
            "amount": round(amount, 2),
            "stop_loss": round(stop_price, 4),
            "take_profit_1": round(res["take_profit_1"], 4),
            "take_profit_2": round(res["take_profit_2"], 4),
            "status": "PENDING"
        }

    if signal == "SELL":
        if cur_qty <= 0:
            return None
        return {
            "timestamp": now_str(),
            "ticker": symbol,
            "signal": "SELL",
            "side": "SELL",
            "price": round(price, 4),
            "qty": cur_qty,
            "amount": round(cur_qty * price, 2),
            "stop_loss": "",
            "take_profit_1": "",
            "take_profit_2": "",
            "status": "PENDING"
        }

    if signal == "REDUCE":
        if cur_qty <= 0:
            return None
        reduce_qty = max(int(cur_qty * 0.5), 1)
        return {
            "timestamp": now_str(),
            "ticker": symbol,
            "signal": "REDUCE",
            "side": "SELL",
            "price": round(price, 4),
            "qty": reduce_qty,
            "amount": round(reduce_qty * price, 2),
            "stop_loss": "",
            "take_profit_1": "",
            "take_profit_2": "",
            "status": "PENDING"
        }

    return None


def apply_fill(positions: dict, ticket: dict) -> dict:
    symbol = ticket["ticker"]
    side = ticket["side"]
    qty = int(ticket["qty"])
    price = float(ticket["price"])

    pos = positions.get(symbol, {"qty": 0, "avg_price": 0.0})
    cur_qty = int(pos.get("qty", 0))
    cur_avg = float(pos.get("avg_price", 0.0))

    if side == "BUY":
        new_qty = cur_qty + qty
        new_avg = ((cur_qty * cur_avg) + (qty * price)) / new_qty if new_qty > 0 else 0.0
        positions[symbol] = {"qty": new_qty, "avg_price": round(new_avg, 4)}

    elif side == "SELL":
        new_qty = max(cur_qty - qty, 0)
        if new_qty == 0:
            positions[symbol] = {"qty": 0, "avg_price": 0.0}
        else:
            positions[symbol] = {"qty": new_qty, "avg_price": cur_avg}

    return positions


# =========================
# Streamlit UI
# =========================
st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title("🛡️ V33.1 國泰手動下單面板")
st.caption("掃描訊號 → 建立下單單 → 你到國泰手動執行 → 回面板標記成交")

state = load_state()
positions = state.get("positions", {})
last_scan = state.get("last_scan", [])
last_orders = state.get("last_orders", [])

with st.expander("🔐 安全提醒", expanded=True):
    st.warning("你剛貼出的 LINE token 已經暴露，建議立刻到 LINE Developers 重發新的 token，並放進 st.secrets 或環境變數，不要再寫死在程式碼。")

# 側欄
with st.sidebar:
    st.header("⚙️ 面板設定")
    watchlist_text = st.text_area("觀察清單", DEFAULT_WATCHLIST, height=160)
    base_capital = st.number_input("模擬總資金", value=BASE_CAPITAL, step=10000)
    refresh_btn = st.button("🔄 立即掃描", use_container_width=True)
    test_line = st.button("📲 測試 LINE 推播", use_container_width=True)

    if test_line:
        ok, msg = push_line(f"V33.1 測試推播\n時間：{now_str()}")
        if ok:
            st.success(msg)
        else:
            st.error(msg)

# 掃描
scan_results = []
watchlist = [x.strip().upper() for x in watchlist_text.split(",") if x.strip()]

if refresh_btn or not last_scan:
    progress = st.progress(0.0)
    for i, symbol in enumerate(watchlist):
        res = calc_engine(symbol)
        if res:
            ticket = None
            preferred_signal = res["signals"][0] if res["signals"] else ""
            if preferred_signal:
                ticket = build_order_ticket(res, preferred_signal, positions)

            row = {
                "代碼": res["ticker"],
                "市場": "美股" if res["is_us"] else "台股",
                "狀態": res["status"],
                "訊號": ",".join(res["signals"]) if res["signals"] else "",
                "現價": round(res["price"], 4),
                "20MA": round(res["m20"], 4),
                "60MA": round(res["m60"], 4),
                "評分": res["score"],
                "風險": res["risk_tag"],
                "停損": round(res["stop_loss_price"], 4),
                "停利1": round(res["take_profit_1"], 4),
                "停利2": round(res["take_profit_2"], 4),
                "大盤": res["market_trend"],
                "圖表": res["chart_url"],
                "_raw": res,
                "_ticket": ticket,
            }
            scan_results.append(row)

            append_csv(LOG_FILE, {
                "timestamp": now_str(),
                "ticker": res["ticker"],
                "status": res["status"],
                "signals": ",".join(res["signals"]),
                "price": round(res["price"], 4),
                "score": res["score"],
                "risk": res["risk_tag"],
            })

        progress.progress((i + 1) / max(len(watchlist), 1))

    scan_results = sorted(scan_results, key=lambda x: (x["評分"], x["狀態"] == "🟢強勢"), reverse=True)
    state["last_scan"] = [
        {k: v for k, v in row.items() if not k.startswith("_")}
        for row in scan_results
    ]
    save_state(state)
else:
    scan_results = [{**row} for row in last_scan]

# 上方摘要
col1, col2, col3, col4 = st.columns(4)
strong_count = sum(1 for r in scan_results if r.get("狀態") == "🟢強勢")
buy_count = sum(1 for r in scan_results if "BUY" in str(r.get("訊號", "")))
sell_count = sum(1 for r in scan_results if "SELL" in str(r.get("訊號", "")))
reduce_count = sum(1 for r in scan_results if "REDUCE" in str(r.get("訊號", "")))

col1.metric("🟢 強勢標的", strong_count)
col2.metric("🟢 BUY 訊號", buy_count)
col3.metric("🔴 SELL 訊號", sell_count)
col4.metric("⚠️ REDUCE 訊號", reduce_count)

# 今日可打3檔
st.subheader("🎯 今日可打 3 檔")
top_candidates = []
for row in scan_results:
    signal_text = str(row.get("訊號", ""))
    if "BUY" in signal_text or row.get("狀態") == "🟢強勢":
        top_candidates.append(row)

top_candidates = sorted(top_candidates, key=lambda x: x["評分"], reverse=True)[:3]

if top_candidates:
    cols = st.columns(3)
    for i, row in enumerate(top_candidates):
        with cols[i]:
            st.markdown(f"### {row['代碼']}")
            st.write(f"狀態：{row['狀態']}")
            st.write(f"訊號：{row['訊號'] or '—'}")
            st.write(f"現價：{row['現價']}")
            st.write(f"停損：{row['停損']}")
            st.write(f"停利1：{row['停利1']}")
            st.write(f"停利2：{row['停利2']}")
            st.write(f"評分：{row['評分']}")
            if row.get("圖表"):
                st.markdown(f"[查看線圖]({row['圖表']})")
else:
    st.info("目前沒有符合條件的主攻標的。")

# 全部掃描結果
st.subheader("📊 全部掃描結果")
if scan_results:
    show_df = pd.DataFrame([
        {
            "代碼": r["代碼"],
            "市場": r["市場"],
            "狀態": r["狀態"],
            "訊號": r["訊號"],
            "現價": r["現價"],
            "20MA": r["20MA"],
            "60MA": r["60MA"],
            "評分": r["評分"],
            "風險": r["風險"],
            "停損": r["停損"],
            "停利1": r["停利1"],
            "停利2": r["停利2"],
            "大盤": r["大盤"],
            "圖表": r["圖表"],
        }
        for r in scan_results
    ])
    st.dataframe(show_df, use_container_width=True, hide_index=True)
else:
    st.warning("尚無掃描結果。")

# 建立手動下單單
st.subheader("📝 國泰手動下單單")

if scan_results:
    selectable = [r["代碼"] for r in scan_results]
    selected_symbol = st.selectbox("選擇標的", selectable, index=0)

    selected_row = next((r for r in scan_results if r["代碼"] == selected_symbol), None)
    raw_signals = []
    if selected_row:
        raw_signal_text = str(selected_row.get("訊號", ""))
        raw_signals = [s for s in raw_signal_text.split(",") if s]

    signal_choice = st.selectbox("選擇動作", raw_signals if raw_signals else ["BUY", "SELL", "REDUCE"])
    default_price = float(selected_row["現價"]) if selected_row else 0.0

    col_a, col_b, col_c = st.columns(3)
    manual_price = col_a.number_input("下單價格", value=default_price, min_value=0.0, step=0.1, format="%.4f")
    manual_qty = col_b.number_input("下單數量", value=0, min_value=0, step=1)
    manual_note = col_c.text_input("備註", value="Cathay manual")

    create_ticket_btn = st.button("建立下單單", use_container_width=True)

    if create_ticket_btn and selected_row:
        raw = None
        # 若剛掃描這輪有 _raw，可用自動計算
        for row in scan_results:
            if row["代碼"] == selected_symbol and "_raw" in row:
                raw = row["_raw"]
                break

        auto_ticket = None
        if raw:
            auto_ticket = build_order_ticket(raw, signal_choice, positions)

        ticket = auto_ticket or {
            "timestamp": now_str(),
            "ticker": selected_symbol,
            "signal": signal_choice,
            "side": "BUY" if signal_choice == "BUY" else "SELL",
            "price": round(manual_price, 4),
            "qty": int(manual_qty),
            "amount": round(manual_price * manual_qty, 2),
            "stop_loss": selected_row.get("停損", ""),
            "take_profit_1": selected_row.get("停利1", ""),
            "take_profit_2": selected_row.get("停利2", ""),
            "status": "PENDING",
        }

        if manual_qty > 0:
            ticket["qty"] = int(manual_qty)
            ticket["amount"] = round(float(ticket["price"]) * int(manual_qty), 2)

        ticket["note"] = manual_note

        last_orders.append(ticket)
        state["last_orders"] = last_orders
        append_csv(ORDERS_FILE, ticket)
        save_state(state)

        st.success("已建立手動下單單")
        st.json(ticket)

        line_msg = (
            f"🏛️ V33.1 手動下單單\n"
            f"標的：{ticket['ticker']}\n"
            f"動作：{ticket['signal']}\n"
            f"價格：{ticket['price']}\n"
            f"數量：{ticket['qty']}\n"
            f"停損：{ticket.get('stop_loss', '')}\n"
            f"停利1：{ticket.get('take_profit_1', '')}\n"
            f"停利2：{ticket.get('take_profit_2', '')}\n"
            f"時間：{ticket['timestamp']}"
        )
        ok, msg = push_line(line_msg)
        if ok:
            st.info("LINE 已推播")
        else:
            st.warning(msg)

# 最近下單單
st.subheader("📦 最近下單單")

if last_orders:
    orders_df = pd.DataFrame(last_orders[::-1])
    st.dataframe(orders_df, use_container_width=True, hide_index=True)

    pending_orders = [o for o in last_orders if o.get("status") == "PENDING"]
    if pending_orders:
        pending_labels = [f"{o['timestamp']} | {o['ticker']} | {o['signal']} | {o['qty']}股 @ {o['price']}" for o in pending_orders]
        selected_pending = st.selectbox("選擇要標記成交的單", pending_labels)

        fill_btn = st.button("✅ 標記已成交", use_container_width=True)
        if fill_btn:
            target_order = pending_orders[pending_labels.index(selected_pending)]
            target_order["status"] = "FILLED"
            positions = apply_fill(positions, target_order)
            state["positions"] = positions
            state["last_orders"] = last_orders
            save_state(state)
            st.success("已標記成交並更新持倉")
            st.rerun()
else:
    st.info("目前尚無下單單。")

# 目前持倉
st.subheader("💼 目前持倉")
if positions:
    pos_df = pd.DataFrame([
        {"代碼": k, "持股數量": v.get("qty", 0), "均價": v.get("avg_price", 0)}
        for k, v in positions.items() if int(v.get("qty", 0)) > 0
    ])
    if not pos_df.empty:
        st.dataframe(pos_df, use_container_width=True, hide_index=True)
    else:
        st.info("目前無有效持倉。")
else:
    st.info("目前無持倉。")

# 底部說明
st.markdown("---")
st.caption("本面板只負責掃描、產生下單單與持倉記錄；實際下單仍由你在國泰手動執行。")
