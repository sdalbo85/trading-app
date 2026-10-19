import streamlit as st
import yfinance as yf
import pandas as pd
import requests

# Configurazione pagina
st.set_page_config(page_title="Screener & Analizzatore Borsa", layout="wide")

st.title("📊 Screener Quantitativo & Trading System")
st.markdown("Sistema automatico per swing trading basato su Trend, RSI, ATR e Volumi.")

# ==========================================
# SIDEBAR - CONFIGURAZIONE E PARAMETRI
# ==========================================
st.sidebar.header("⚙️ Configurazione Watchlist")

default_watchlist = "NVDA, AMD, AVGO, ARM, PLTR, PANW, CRWD, NET, VST, CEG, VRT, ANET, AMZN, SHOP, MELI, CELH, COIN, UBER, PYPL, TSLA"
watchlist_input = st.sidebar.text_area("Inserisci la tua Watchlist (separata da virgola):", value=default_watchlist, height=120)
WATCHLIST = [ticker.strip().upper() for ticker in watchlist_input.split(",") if ticker.strip()]

period_option = st.sidebar.selectbox("Periodo Storico:", ["1y", "6m", "2y"], index=0)

st.sidebar.header("🛡️ Gestione Rischio & Guadagno")

CAPITAL = st.sidebar.number_input("Capitale Totale (€/$):", value=1000.0, step=100.0)
MAX_RISK_PCT = st.sidebar.slider("Rischio Max (%):", min_value=0.5, max_value=5.0, value=2.0, step=0.5)
RR_RATIO = st.sidebar.slider("Rapporto Risk/Reward (es. 1:2 o 1:3):", min_value=1.0, max_value=4.0, value=2.0, step=0.5)

st.sidebar.header("📲 Notifiche Telegram")
TELEGRAM_TOKEN = st.sidebar.text_input("Bot Token:", value="8880305168:AAEwG78l80y4HOwwgy18byQ6swNSo-XxlJY", type="password")
TELEGRAM_CHAT_ID = st.sidebar.text_input("Chat ID:", value="8821873237")

if st.sidebar.button("🧪 Invia Test Telegram"):
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": "✅ **Test Telegram Streamlit:** Connessione riuscita!", "parse_mode": "Markdown"}
        try:
            res = requests.post(url, json=payload, timeout=5)
            if res.status_code == 200:
                st.sidebar.success("Messaggio inviato con successo!")
            else:
                st.sidebar.error(f"Errore Telegram ({res.status_code})")
        except Exception as e:
            st.sidebar.error(f"Errore connessione: {e}")
    else:
        st.sidebar.warning("Inserisci Token e Chat ID")

# ==========================================
# FUNZIONI DI CALCOLO
# ==========================================
def calculate_rsi(data, period=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_atr(df, period=14):
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift()).abs()
    low_close = (df['Low'] - df['Close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

@st.cache_data(ttl=3600)
def load_data(tickers, period):
    results = []
    for ticker in tickers:
        try:
            df = yf.download(ticker, period=period, interval="1d", progress=False)
            if df.empty or len(df) < 200:
                continue

            if isinstance(df.columns, pd.MultiIndex):
                df = df.xs(ticker, axis=1,
