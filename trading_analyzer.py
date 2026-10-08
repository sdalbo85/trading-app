import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests

# Configurazione pagina Streamlit
st.set_page_config(page_title="Trading Screener & Analyzer", layout="wide")

st.title("📈 Screener e Analizzatore di Borsa Multi-Titolo")

# --- SIDEBAR: PARAMETRI E WATCHLIST ---
st.sidebar.header("⚙️ Gestione Rischio & Guadagno")

watchlist_input = st.sidebar.text_area(
    "Inserisci la Watchlist (separata da virgola):",
    value="ANET, CSCO, MRVL, CRDO, CEG, VST, VRT, SU, EQIX, BYDDY, NVO, TSLA, PLTR, AMD, NET, COIN, ARM, CELH, SHOP, UBER, PATH, PANW"
)

capitale = st.sidebar.number_input("Capitale Totale (€/$):", value=10000.0, step=500.0)
max_risk_pct = st.sidebar.slider("Rischio Max (%):", 0.5, 5.0, 2.0, 0.1)
stop_loss_pct = st.sidebar.slider("Stop Loss (%):", 1.0, 10.0, 3.0, 0.5)
rr_ratio = st.sidebar.slider("Rapporto Risk/Reward (es. 1:2 o 1:3):", 1.0, 5.0, 2.0, 0.5)

calculated_tp = stop_loss_pct * rr_ratio
st.sidebar.info(f"🎯 **Target Take Profit:** +{calculated_tp:.1f}% dal prezzo di acquisto")

# --- FUNZIONI CALCOLO ---
def calculate_rsi(data, period=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

tickers = [t.strip().upper() for t in watchlist_input.split(",") if t.strip()]

st.button("🔄 Aggiorna Dati Watchlist")

results = []

with st.spinner("Caricamento e analisi dati di mercato in corso..."):
    for ticker in tickers:
        try:
            df = yf.download(ticker, period="6m", interval="1d", progress=False, auto_adjust=True)
            if df.empty or len(df) < 50:
                continue

            # Gestione colonne MultiIndex
            if isinstance(df.columns, pd.MultiIndex):
                close_prices = df["Close"][ticker]
                volume_data = df["Volume"][ticker]
            else:
                close_prices = df["Close"]
                volume_data = df["Volume"]

            prezzo_attuale = float(close_prices.iloc[-1])
            sma50 = float(close_prices.rolling(window=50).mean().iloc[-1])
            rsi = float(calculate_rsi(close_prices, period=14).iloc[-1])
            
            vol_attuale = float(volume_data.iloc[-1])
            vol_sma20 = float(volume_data.rolling(window=20).mean().iloc[-1])
            forza_volumi = "🔥 Alti" if vol_attuale > vol_sma20 else "❄️ Normali"

            # Logica del Segnale
            if prezzo_attuale > sma50 and rsi < 45:
                decision = "🟢 COMPRA"
            elif rsi > 70 or prezzo_attuale < sma50:
                decision = "🔴 VENDI / FUORI"
            else:
                decision = "⚪ ATTENDI"

            # Money Management
            if decision == "🟢 COMPRA":
                max_risk_amount = capitale * (max_risk_pct / 100.0)
                sl_target = prezzo_attuale * (1 - (stop_loss_pct / 100.0))
                tp_pct = stop_loss_pct * rr_ratio
                tp_target = prezzo_attuale * (1 + (tp_pct / 100.0))
                
                risk_per_share = prezzo_attuale - sl_target
                shares = int(max_risk_amount / risk_per_share) if risk_per_share > 0 else 0
                req_capital = shares * prezzo_attuale
            else:
                shares = 0
                sl_target = 0.0
                tp_target = 0.0
                req_capital = 0.0

            results.append({
                "Ticker": ticker,
                "Prezzo ($/€)": round(prezzo_attuale, 2),
                "Decisione Algoritmo": decision,
                "RSI (14)": round(rsi, 2),
                "Forza Volumi": forza_volumi,
                "Sopra SMA50": "Sì" if prezzo_attuale > sma50 else "No",
                "Azioni Consigliate": shares,
                "Stop Loss Target ($)": round(sl_target, 2),
                "Take Profit Target ($)": round(tp_target, 2),
                "Capitale Richiesto ($/€)": round(req_capital, 2)
            })
        except Exception:
            continue

df_results = pd.DataFrame(results)

# --- TABELLA PRINCIPALE ---
if not df_results.empty:
    st.subheader("📋 Tabella Monitoraggio In Tempo Reale")
    st.dataframe(df_results, use_container_width=True)

    # --- SEZIONE GRAFICO SINGOLO TITOLO ---
    st.markdown("---")
    st.subheader("📈 Analisi Grafica Singolo Titolo")

    selected_ticker = st.selectbox("Seleziona un titolo per visual
