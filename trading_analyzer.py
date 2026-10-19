import streamlit as st
import yfinance as yf
import pandas as pd

# Configurazione pagina
st.set_page_config(page_title="Screener & Analizzatore Borsa", layout="wide")

st.title("📊 Screener Quantitativo & Trading System")
st.markdown("Sistema automatico per swing trading basato su Trend, RSI, ATR e Volumi.")

# Sidebar - Parametri
st.sidebar.header("⚙️ Parametri Strategia")

CAPITAL = st.sidebar.number_input("Capitale Totale (€)", value=1000.0, step=100.0)
MAX_RISK_PCT = st.sidebar.slider("Rischio Max per Trade (%)", min_value=0.5, max_value=5.0, value=2.0, step=0.5)
RR_RATIO = st.sidebar.slider("Rapporto Risk/Reward (1:N)", min_value=1.0, max_value=4.0, value=2.0, step=0.5)

WATCHLIST = [
    "NVDA", "AMD", "AVGO", "ARM", "PLTR", "PANW", "CRWD", "NET", 
    "VST", "CEG", "VRT", "ANET", "AMZN", "SHOP", "MELI", "CELH", 
    "COIN", "UBER", "PYPL", "TSLA"
]

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
def load_data():
    results = []
    for ticker in WATCHLIST:
        try:
            df = yf.download(ticker, period="1y", interval="1d", progress=False)
            if df.empty or len(df) < 200:
                continue

            if isinstance(df.columns, pd.MultiIndex):
                df = df.xs(ticker, axis=1, level=1)

            close = df['Close']
            volume = df['Volume']

            sma_50 = close.rolling(window=50).mean()
            sma_200 = close.rolling(window=200).mean()
            vol_sma_20 = volume.rolling(window=20).mean()
            rsi = calculate_rsi(close, period=14)
            atr = calculate_atr(df, period=14)

            current_price = float(close.iloc[-1])
            prev_price = float(close.iloc[-2])
            current_sma50 = float(sma_50.iloc[-1])
            current_sma200 = float(sma_200.iloc[-1])
            current_rsi = float(rsi.iloc[-1])
            prev_rsi = float(rsi.iloc[-2])
            current_vol = float(volume.iloc[-1])
            avg_vol = float(vol_sma_20.iloc[-1])
            current_atr = float(atr.iloc[-1])

            # Filtri di ingresso
            cond_trend = current_price > current_sma50
            cond_pullback = current_rsi < 48
            cond_rsi_rebound = current_rsi > prev_rsi
            cond_price_rebound = current_price > prev_price

            signal = "🔴 ATTESA"
            rating_score = 0
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
        except Exception as e:
            continue

    return pd.DataFrame(results)

with st.spinner("Caricamento dati di borsa in corso..."):
    data_df = load_data()

if not data_df.empty:
    st.subheader("📋 Watchlist e Segnali in Tempo Reale")
    
    # Evidenzia i segnali di acquisto (utilizzando .map al posto di .applymap)
    def highlight_buy(val):
        color = 'background-color: #1e4620; color: white' if val == "🟢 COMPRA" else ''
        return color

    if hasattr(data_df.style, 'map'):
        styled_df = data_df.style.map(highlight_buy, subset=['Segnale'])
    else:
        styled_df = data_df.style.applymap(highlight_buy, subset=['Segnale'])

    st.dataframe(styled_df, use_container_width=True)
else:
    st.error("Impossibile scaricare i dati. Riprova più tardi.")
