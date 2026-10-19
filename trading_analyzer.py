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
WATCHLIST = [t.strip().upper() for t in watchlist_input.split(",") if t.strip()]

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
                st.sidebar.success("Messaggio inviato!")
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

def calculate_atr(high, low, close, period=14):
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def load_data(tickers, period):
    results = []
    for ticker in tickers:
        try:
            df = yf.download(ticker, period=period, interval="1d", progress=False)
            if df.empty or len(df) < 50:
                continue

            if isinstance(df.columns, pd.MultiIndex):
                df = df.xs(ticker, axis=1, level=1)

            close = df['Close']
            volume = df['Volume']
            high = df['High']
            low = df['Low']

            sma_50 = close.rolling(50).mean()
            sma_200 = close.rolling(200).mean()
            vol_sma_20 = volume.rolling(20).mean()
            rsi = calculate_rsi(close)
            atr = calculate_atr(high, low, close)

            current_price = float(close.iloc[-1])
            prev_price = float(close.iloc[-2])
            current_sma50 = float(sma_50.iloc[-1]) if not pd.isna(sma_50.iloc[-1]) else current_price
            current_sma200 = float(sma_200.iloc[-1]) if not pd.isna(sma_200.iloc[-1]) else current_price
            current_rsi = float(rsi.iloc[-1])
            prev_rsi = float(rsi.iloc[-2])
            current_vol = float(volume.iloc[-1])
            avg_vol = float(vol_sma_20.iloc[-1]) if not pd.isna(vol_sma_20.iloc[-1]) else current_vol
            current_atr = float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else current_price * 0.02

            cond_trend = current_price > current_sma50
            cond_pullback = current_rsi < 48
            cond_rsi_rebound = current_rsi > prev_rsi
            cond_price_rebound = current_price > prev_price

            signal = "🔴 ATTESA"
            stars = "-"
            sl_target = 0.0
            tp_target = 0.0
            shares = 0

            if cond_trend and cond_pullback and cond_rsi_rebound and cond_price_rebound:
                signal = "🟢 COMPRA"
                rating_score = 2
                if current_price > current_sma200:
                    rating_score += 1
                if current_vol > avg_vol:
                    rating_score += 1
                stars = "⭐" * rating_score

                max_risk_amount = CAPITAL * (MAX_RISK_PCT / 100.0)
                sl_distance = current_atr * 2.0
                sl_target = current_price - sl_distance
                tp_target = current_price + (sl_distance * RR_RATIO)
                
                shares = int(max_risk_amount / sl_distance) if sl_distance > 0 else 0
                if shares < 1:
                    shares = 1

            results.append({
                "Ticker": ticker,
                "Prezzo ($)": round(current_price, 2),
                "Segnale": signal,
                "Rating": stars,
                "RSI": round(current_rsi, 1),
                "Stop Loss ($)": round(sl_target, 2) if sl_target > 0 else "-",
                "Take Profit ($)": round(tp_target, 2) if tp_target > 0 else "-",
                "Azioni Consigliate": shares if shares > 0 else "-",
                "Sopramedia 200": "Sì" if current_price > current_sma200 else "No",
                "Volumi Alti": "Sì" if current_vol > avg_vol else "No"
            })
        except Exception:
            continue

    return pd.DataFrame(results)

# ==========================================
# INTERFACCIA PRINCIPALE
# ==========================================
with st.spinner("Caricamento dati di borsa in corso..."):
    data_df = load_data(WATCHLIST, period_option)

if not data_df.empty:
    st.subheader("📋 Watchlist e Segnali in Tempo Reale")
    def highlight_buy(val):
        return 'background-color: #1e4620; color: white' if val == "🟢 COMPRA" else ''

    if hasattr(data_df.style, 'map'):
        styled_
