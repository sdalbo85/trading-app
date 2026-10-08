import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objects as go

st.set_page_config(page_title="Trading Screener", layout="wide")
st.title("📈 Trading Screener & Analyzer")

# --- SIDEBAR ---
st.sidebar.header("⚙️ Impostazioni Rischio")

watchlist_input = st.sidebar.text_area(
    "Watchlist (separata da virgola):",
    value="ANET, CSCO, MRVL, CRDO, CEG, VST, VRT, SU, EQIX, BYDDY, NVO, TSLA, PLTR, AMD, NET, COIN, ARM, CELH, SHOP, UBER, PATH, PANW"
)

capitale = st.sidebar.number_input("Capitale Totale:", value=10000.0, step=500.0)
max_risk_pct = st.sidebar.slider("Rischio Max (%):", 0.5, 5.0, 2.0, 0.1)
stop_loss_pct = st.sidebar.slider("Stop Loss (%):", 1.0, 10.0, 3.0, 0.5)
rr_ratio = st.sidebar.slider("Risk/Reward Ratio:", 1.0, 5.0, 2.0, 0.5)

# --- CALCOLI ---
def calculate_rsi(data, period=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

tickers = [t.strip().upper() for t in watchlist_input.split(",") if t.strip()]

if st.button("🔄 Aggiorna Dati"):
    st.cache_data.clear()

results = []

# Creazione sessione personalizzata con User-Agent browser per bypassare il blocco
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
})

with st.spinner("Caricamento dati di mercato in corso..."):
    for ticker in tickers:
        try:
            t_obj = yf.Ticker(ticker, session=session)
            df = t_obj.history(period="6m", interval="1d")
            
            if df.empty or len(df) < 50:
                continue

            close_prices = df["Close"]
            volume_data = df["Volume"]

            prezzo_attuale = float(close_prices.iloc[-1])
            sma50 = float(close_prices.rolling(window=50).mean().iloc[-1])
            rsi = float(calculate_rsi(close_prices, period=14).iloc[-1])
            
            vol_attuale = float(volume_data.iloc[-1])
            vol_sma20 = float(volume_data.rolling(window=20).mean().iloc[-1])
            forza_volumi = "🔥 Alti" if vol_attuale > vol_sma20 else "❄️ Normali"

            if prezzo_attuale > sma50 and rsi < 45:
                decision = "🟢 COMPRA"
            elif rsi > 70 or prezzo_attuale < sma50:
                decision = "🔴 VENDI"
            else:
                decision = "⚪ ATTENDI"

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
                "Prezzo ($)": round(prezzo_attuale, 2),
                "Decisione": decision,
                "RSI": round(rsi, 2),
                "Volumi": forza_volumi,
                "Sopra SMA50": "Si" if prezzo_attuale > sma50 else "No",
                "Azioni": shares,
                "Stop Loss ($)": round(sl_target, 2),
                "Take Profit ($)": round(tp_target, 2),
                "Capitale ($)": round(req_capital, 2)
            })
        except Exception:
            continue

df_results = pd.DataFrame(results)

# --- VISUALIZZAZIONE ---
if not df_results.empty:
    st.subheader("📋 Tabella Monitoraggio")
    st.dataframe(df_results, use_container_width=True)

    st.markdown("---")
    st.subheader("📈 Grafico Singolo Titolo")

    ticker_list = df_results["Ticker"].tolist()
    selected_ticker = st.selectbox("Seleziona Titolo:", ticker_list)

    if selected_ticker:
        try:
            t_obj_chart = yf.Ticker(selected_ticker, session=session)
            data_chart = t_obj_chart.history(period="6m", interval="1d")
            
            if not data_chart.empty:
                chart_close = data_chart["Close"]
                sma50_chart = chart_close.rolling(window=50).mean()

                fig = go.Figure()
                fig.add_trace(go.Scatter(x=data_chart.index, y=chart_close, mode="lines", name="Prezzo"))
                fig.add_trace(go.Scatter(x=data_chart.index, y=sma50_chart, mode="lines", name="SMA 50"))

                fig.update_layout(
                    title=f"Prezzo e SMA 50: {selected_ticker}",
                    xaxis_title="Data",
                    yaxis_title="Prezzo ($)",
                    template="plotly_white",
                    height=500
                )

                st.plotly_chart(fig, use_container_width=True)
        except Exception:
            st.warning("Grafico non disponibile.")
else:
    st.warning("Nessun dato disponibile al momento. Prova a fare clic su '🔄 Aggiorna Dati'.")
