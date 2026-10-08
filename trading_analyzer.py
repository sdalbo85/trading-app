import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
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

with st.spinner("Caricamento dati di mercato..."):
    try:
        # Download batch unico per tutti i ticker
        data_all = yf.download(tickers, period="6m", interval="1d", progress=False, auto_adjust=True)
        
        for ticker in tickers:
            try:
                if isinstance(data_all.columns, pd.MultiIndex):
                    close_prices = data_all["Close"][ticker].dropna()
                    volume_data = data_all["Volume"][ticker].dropna()
                else:
                    close_prices = data_all["Close"].dropna()
                    volume_data = data_all["Volume"].dropna()

                if len(close_prices) < 50:
                    continue

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
    except Exception as e:
        st.error(f"Errore download batch: {e}")

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
            if isinstance(data_all.columns, pd.MultiIndex):
                chart_close = data_all["Close"][selected_ticker].dropna()
            else:
                chart_close = data_all["Close"].dropna()

            sma50_chart = chart_close.rolling(window=50).mean()

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=chart_close.index, y=chart_close, mode="lines", name="Prezzo"))
            fig.add_trace(go.Scatter(x=chart_close.index, y=sma50_chart, mode="lines", name="SMA 50"))

            fig.update_layout(
                title=f"Prezzo e SMA 50: {selected_ticker}",
                xaxis_title="Data",
                yaxis_title="Prezzo ($)",
                template="plotly_white",
                height=500
            )

            st.plotly_chart(fig, use_container_width=True)
        except Exception:
            st.warning("Grafico non disponibile per questo titolo.")
else:
    st.warning("Nessun dato disponibile al momento. Prova a fare clic su '🔄 Aggiorna Dati'.")
