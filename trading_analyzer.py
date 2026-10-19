import streamlit as st
import yfinance as yf
import pandas as pd
import requests

st.set_page_config(page_title="Screener Quantitativo", layout="wide")

st.title("📊 Screener Quantitativo & Trading System")
st.markdown("Sistema automatico per swing trading basato su Trend, RSI, ATR e Volumi.")

# SIDEBAR
st.sidebar.header("⚙️ Configurazione Watchlist")
default_wl = "NVDA, AMD, AVGO, ARM, PLTR, PANW, CRWD, NET, VST, CEG, VRT, ANET, AMZN, SHOP, MELI, CELH, COIN, UBER, PYPL, TSLA"
wl_input = st.sidebar.text_area("Watchlist (separata da virgola):", value=default_wl, height=100)
WATCHLIST = [t.strip().upper() for t in wl_input.split(",") if t.strip()]

period_option = st.sidebar.selectbox("Periodo Storico:", ["1y", "6m", "2y"], index=0)

st.sidebar.header("🛡️ Gestione Rischio")
CAPITAL = st.sidebar.number_input("Capitale Totale (€/$):", value=1000.0, step=100.0)
MAX_RISK_PCT = st.sidebar.slider("Rischio Max (%):", min_value=0.5, max_value=5.0, value=2.0, step=0.5)
RR_RATIO = st.sidebar.slider("Rapporto Risk/Reward:", min_value=1.0, max_value=4.0, value=2.0, step=0.5)

st.sidebar.header("📲 Notifiche Telegram")
TELEGRAM_TOKEN = st.sidebar.text_input("Bot Token:", value="8880305168:AAEwG78l80y4HOwwgy18byQ6swNSo-XxlJY", type="password")
TELEGRAM_CHAT_ID = st.sidebar.text_input("Chat ID:", value="8821873237")

if st.sidebar.button("🧪 Invia Test Telegram"):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": "✅ Test Telegram OK!", "parse_mode": "Markdown"}
        try:
            res = requests.post(url, json=payload, timeout=5)
            if res.status_code == 200:
                st.sidebar.success("Messaggio inviato!")
            else:
                st.sidebar.error(f"Errore {res.status_code}")
        except Exception as e:
            st.sidebar.error(f"Errore: {e}")

# CALCOLI
def get_rsi(series, p=14):
    d = series.diff()
    g = d.where(d > 0, 0).rolling(p).mean()
    l = (-d.where(d < 0, 0)).rolling(p).mean()
    return 100 - (100 / (1 + (g / l)))

def get_atr(df, p=14):
    tr = pd.concat([df['High']-df['Low'], (df['High']-df['Close'].shift()).abs(), (df['Low']-df['Close'].shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(p).mean()

def load_data(tickers, period):
    res = []
    for t in tickers:
        try:
            df = yf.download(t, period=period, interval="1d", progress=False)
            if df.empty or len(df) < 50:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df = df.xs(t, axis=1, level=1)

            c, v = df['Close'], df['Volume']
            p_now, p_prev = float(c.iloc[-1]), float(c.iloc[-2])
            sma50, sma200 = float(c.rolling(50).mean().iloc[-1]), float(c.rolling(200).mean().iloc[-1])
            
            rsi_s = get_rsi(c)
            rsi_now, rsi_prev = float(rsi_s.iloc[-1]), float(rsi_s.iloc[-2])
            
            v_now, v_avg = float(v.iloc[-1]), float(v.rolling(20).mean().iloc[-1])
            atr_val = float(get_atr(df).iloc[-1])

            cond_trend = p_now > sma50
            cond_pullback = rsi_now < 48
            cond_rsi_up = rsi_now > rsi_prev
            cond_price_up = p_now > p_prev

            sig, stars, sl, tp, sh = "🔴 ATTESA", "-", 0.0, 0.0, 0

            if cond_trend and cond_pullback and cond_rsi_up and cond_price_up:
                sig = "🟢 COMPRA"
                score = 2 + (1 if p_now > sma200 else 0) + (1 if v_now > v_avg else 0)
                stars = "⭐" * score
                
                risk_eur = CAPITAL * (MAX_RISK_PCT / 100.0)
                sl_dist = atr_val * 2.0
                sl = p_now - sl_dist
                tp = p_now + (sl_dist * RR_RATIO)
                sh = max(1, int(risk_eur / sl_dist)) if sl_dist > 0 else 1

            res.append({
                "Ticker": t,
                "Prezzo ($)": round(p_now, 2),
                "Segnale": sig,
                "Rating": stars,
                "RSI": round(rsi_now, 1),
                "Stop Loss ($)": round(sl, 2) if sl > 0 else "-",
                "
