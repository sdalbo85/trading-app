import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import requests

st.set_page_config(page_title="Trading Screener", layout="wide")
st.title("Trading Screener & Analyzer")

# --- SIDEBAR ---
st.sidebar.header("Configurazione")

watchlist_input = st.sidebar.text_area(
    "Inserisci la Watchlist (separata da virgola):",
    value="ANET, CSCO, MRVL, CRDO, CEG, VST, VRT, SU, EQIX, BYDDY, NVO, TSLA, PLTR, AMD, NET, COIN, ARM, CELH, SHOP, UBER, PATH, PANW"
)

capitale = st.sidebar.number_input("Capitale Totale ($):", value=10000, step=500)
rischio_pct = st.sidebar.slider("Rischio Max per Trade (%):", 0.5, 5.0, 2.0) / 100
stop_loss_pct = st.sidebar.slider("Stop Loss (%):", 1.0, 10.0, 3.0) / 100

st.sidebar.subheader("Test Telegram")
telegram_token = st.sidebar.text_input("Bot Token:", type="password")
telegram_chat_id = st.sidebar.text_input("Chat ID:")

if st.sidebar.button("Testa Notifica Telegram"):
    if telegram_token and telegram_chat_id:
        url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        payload = {"chat_id": telegram_chat_id, "text": "Test notifica riuscito!"}
        res = requests.post(url, json=payload)
        if res.status_code == 200:
            st.sidebar.success("Messaggio inviato!")
        else:
            st.sidebar.error("Errore invio Telegram.")
    else:
        st.sidebar.warning("Inserisci Token e Chat ID.")

# --- ELABORAZIONE DATI IN CACHE (Protezione da Rate-Limit) ---
tickers = [t.strip().upper() for t in watchlist_input.split(",") if t.strip()]

def calcola_rsi(series, window=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

@st.cache_data(ttl=1800)  # Salva i dati in cache per 30 minuti
def scarica_dati_watchlist(lista_ticker):
    dati_raccolti = []
    for ticker in lista_ticker:
        try:
            df = yf.download(ticker, period="6m", interval="1d", progress=False, auto_adjust=True)
            if not df.empty and len(df) >= 50:
                dati_raccolti.append((ticker, df))
        except Exception:
            continue
    return dati_raccolti

if st.button("🔄 Aggiorna Dati Watchlist"):
    st.cache_data.clear()

results = []

with st.spinner("Caricamento dati di mercato..."):
    dati = scarica_dati_watchlist(tickers)
    
    for ticker, df in dati:
        try:
            close_prices = df["Close"].squeeze()
            volume_data = df["Volume"].squeeze()

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

# --- TABELLA E GRAFICO ---
if not df_results.empty:
    st.subheader("Tabella Analisi Live")
    st.dataframe(df_results, use_container_width=True)

    st.markdown("---")
    st.subheader("Analisi Grafica Singolo Titolo")

    selected_ticker = st.selectbox("Seleziona un titolo:", df_results["Ticker"].tolist())

    if selected_ticker:
        # Recupera il DataFrame del ticker selezionato direttamente dalla memoria
        df_chart = next((df for t, df in dati if t == selected_ticker), None)

        if df_chart is not None and not df_chart.empty:
            chart_close = df_chart["Close"].squeeze()
            sma50_chart = chart_close.rolling(window=50).mean()

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_chart.index, y=chart_close, mode="lines", name="Prezzo", line=dict(color="#1f77b4", width=2)))
            fig.add_trace(go.Scatter(x=df_chart.index, y=sma50_chart, mode="lines", name="SMA 50", line=dict(color="#ff7f0e", width=2)))

            fig.update_layout(
                title=f"Grafico Prezzo e SMA 50 - {selected_ticker}",
                xaxis_title="Data",
                yaxis_title="Prezzo ($)",
                template="plotly_white",
                height=500
            )

            st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Nessun dato caricato. Prova a cliccare su '🔄 Aggiorna Dati Watchlist'.")
