import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests
import time

# Configurazione pagina Streamlit
st.set_page_config(page_title="Trading Screener", layout="wide")

st.title("Trading Screener & Analyzer")

# --- SIDEBAR: PARAMETRI E WATCHLIST ---
st.sidebar.header("Configurazione")

watchlist_input = st.sidebar.text_area(
    "Inserisci la Watchlist (separata da virgola):",
    value="ANET, CSCO, MRVL, CRDO, CEG, VST, VRT, SU, EQIX, BYDDY, NVO, TSLA, PLTR, AMD, NET, COIN, ARM, CELH, SHOP, UBER, PATH, PANW"
)

capitale = st.sidebar.number_input("Capitale Totale ($):", value=10000, step=500)
rischio_pct = st.sidebar.slider("Rischio Max per Trade (%):", 0.5, 5.0, 2.0) / 100
stop_loss_pct = st.sidebar.slider("Stop Loss (%):", 1.0, 10.0, 3.0) / 100

# Parametri Telegram facoltativi per test
st.sidebar.subheader("Test Telegram")
telegram_token = st.sidebar.text_input("Bot Token:", type="password")
telegram_chat_id = st.sidebar.text_input("Chat ID:")

if st.sidebar.button("Testa Notifica Telegram"):
    if telegram_token and telegram_chat_id:
        url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        payload = {"chat_id": telegram_chat_id, "text": "Test notifica da Streamlit riuscito!"}
        res = requests.post(url, json=payload)
        if res.status_code == 200:
            st.sidebar.success("Messaggio inviato!")
        else:
            st.sidebar.error(f"Errore Telegram: {res.text}")
    else:
        st.sidebar.warning("Inserisci Token e Chat ID per il test.")

# --- ELABORAZIONE DATI ---
tickers = [t.strip().upper() for t in watchlist_input.split(",") if t.strip()]

def calcola_rsi(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

if st.button("🔄 Aggiorna Dati Watchlist"):
    st.cache_data.clear()

results = []

with st.spinner("Analisi dei dati di mercato in corso..."):
    for ticker in tickers:
        try:
            # Scarica singolarmente con gestione sicura dei dati
            df = yf.download(ticker, period="6m", interval="1d", progress=False)
            
            if df.empty or len(df) < 50:
                continue

            # Pulizia colonne MultiIndex se presente
            if isinstance(df.columns, pd.MultiIndex):
                close_prices = df["Close"][ticker]
                volume_data = df["Volume"][ticker]
            else:
                close_prices = df["Close"]
                volume_data = df["Volume"]

            prezzo_attuale = float(close_prices.iloc[-1])
            sma50 = float(close_prices.rolling(50).mean().iloc[-1])
            rsi = float(calcola_rsi(close_prices).iloc[-1])
            
            vol_attuale = float(volume_data.iloc[-1])
            vol_sma20 = float(volume_data.rolling(20).mean().iloc[-1])
            forza_volumi = "Alti" if vol_attuale > vol_sma20 else "Normali"

            if prezzo_attuale > sma50 and rsi < 45:
                segnale = "COMPRA"
            elif prezzo_attuale < sma50 or rsi > 70:
                segnale = "VENDI"
            else:
                segnale = "ATTENDI"

            stop_loss_price = prezzo_attuale * (1 - stop_loss_pct)
            take_profit_price = prezzo_attuale * (1 + (stop_loss_pct * 2))
            rischio_dollari = capitale * rischio_pct
            perdita_per_azione = prezzo_attuale - stop_loss_price
            azioni_consigliate = int(rischio_dollari / perdita_per_azione) if perdita_per_azione > 0 else 0

            results.append({
                "Ticker": ticker,
                "Segnale": segnale,
                "Prezzo ($)": round(prezzo_attuale, 2),
                "RSI (14)": round(rsi, 2),
                "SMA 50 ($)": round(sma50, 2),
                "Forza Volumi": forza_volumi,
                "Stop Loss ($)": round(stop_loss_price, 2),
                "Take Profit ($)": round(take_profit_price, 2),
                "Azioni Consigliate": azioni_consigliate
            })
        except Exception:
            continue

df_results = pd.DataFrame(results)

# --- TABELLA PRINCIPALE ---
if not df_results.empty:
    st.subheader("Tabella Analisi Live")
    st.dataframe(df_results, use_container_width=True)

    # --- SEZIONE GRAFICO SINGOLO TITOLO ---
    st.markdown("---")
    st.subheader("Analisi Grafica Singolo Titolo")

    selected_ticker = st.selectbox("Seleziona un titolo per visualizzare il grafico:", df_results["Ticker"].tolist())

    if selected_ticker:
        try:
            data_chart = yf.download(selected_ticker, period="6m", interval="1d", progress=False)

            if not data_chart.empty:
                if isinstance(data_chart.columns, pd.MultiIndex):
                    chart_close = data_chart["Close"][selected_ticker]
                else:
                    chart_close = data_chart["Close"]

                sma50_chart = chart_close.rolling(window=50).mean()

                fig = go.Figure()
                fig.add_trace(go.Scatter(x=data_chart.index, y=chart_close, mode="lines", name="Prezzo di Chiusura", line=dict(color="#1f77b4", width=2)))
                fig.add_trace(go.Scatter(x=data_chart.index, y=sma50_chart, mode="lines", name="SMA 50", line=dict(color="#ff7f0e", width=2)))

                fig.update_layout(
                    title=f"Grafico Prezzo e SMA 50 - {selected_ticker}",
                    xaxis_title="Data",
                    yaxis_title="Prezzo ($)",
                    template="plotly_white",
                    height=500
                )

                st.plotly_chart(fig, use_container_width=True)
        except Exception:
            st.warning("Impossibile caricare il grafico per questo titolo.")
else:
    st.warning("Mercato chiuso o aggiornamento in corso. Prova a ridurre leggermente la watchlist se Yahoo blocca le richieste.")
