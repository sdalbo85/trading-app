import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objects as go

# ==========================================
# 1. CONFIGURAZIONE TELEGRAM
# ==========================================
TELEGRAM_TOKEN = "8880305168:AAEwG78l80y4HOwwgy18byQ6swNSo-XxlJY"
TELEGRAM_CHAT_ID = "8821873237"

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        res_data = response.json()
        if response.status_code == 200:
            return True, "OK"
        else:
            return False, res_data.get("description", "Errore sconosciuto da Telegram")
    except Exception as e:
        return False, str(e)

# ==========================================
# 2. FUNZIONI CALCOLO INDICATORI (RSI & ATR)
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

def analyze_ticker(ticker, capital, max_risk_pct, rr_ratio):
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if df.empty or len(df) < 200:
            return None
        
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
        current_sma50 = float(sma_50.iloc[-1])
        current_sma200 = float(sma_200.iloc[-1])
        current_rsi = float(rsi.iloc[-1])
        current_vol = float(volume.iloc[-1])
        avg_vol = float(vol_sma_20.iloc[-1])
        current_atr = float(atr.iloc[-1])

        # Logica del Segnale Invariata (Trigger Reattivo)
        if current_price > current_sma50 and current_rsi < 45:
            decision = "🟢 COMPRA"
        elif current_rsi > 70 or current_price < current_sma50:
            decision = "🔴 VENDI / FUORI"
        else:
            decision = "⚪ ATTENDI"

        # Punteggio di Confluenza (Quality Rating)
        rating_score = 0
        if decision == "🟢 COMPRA":
            rating_score = 2  # Base (Sopra SMA50 + RSI<45)
            if current_price > current_sma200:
                rating_score += 1  # Bonus Super-Trend
            if current_vol > avg_vol:
                rating_score += 1  # Bonus Volumi
            stars = "⭐" * rating_score
        else:
            stars = "-"

        # Risk Management Dinamico basato su ATR (1.5 x ATR)
        if decision == "🟢 COMPRA":
            max_risk_amount = capital * (max_risk_pct / 100.0)
            
            # Stop Loss e Take Profit proporzionati alla volatilità reale
            sl_distance = current_atr * 1.5
            sl_target = current_price - sl_distance
            tp_target = current_price + (sl_distance * rr_ratio)
            
            shares = int(max_risk_amount / sl_distance) if sl_distance > 0 else 0
            req_capital = shares * current_price
        else:
            shares = 0
            sl_target = 0.0
            tp_target = 0.0
            req_capital = 0.0

        return {
            "Ticker": ticker,
            "Prezzo ($/€)": round(current_price, 2),
            "Decisione Algoritmo": decision,
            "Rating Qualità": stars,
            "RSI (14)": round(current_rsi, 2),
            "Forza Volumi": "🔥 Alti" if current_vol > avg_vol else "❄️ Normali",
            "Sopra SMA200": "Sì" if current_price > current_sma200 else "No",
            "Stop Loss (ATR $)": round(sl_target, 2),
            "Take Profit Target ($)": round(tp_target, 2),
            "Azioni Consigliate": shares,
            "Capitale Richiesto ($/€)": round(req_capital, 2)
        }
    except Exception as e:
        st.error(f"Errore nell'analisi di {ticker}: {e}")
        return None

# ==========================================
# 3. INTERFACCIA UTENTE STREAMLIT
# ==========================================
st.set_page_config(page_title="Screener & Analizzatore Borsa", layout="wide")
st.title("📈 Screener e Analizzatore di Borsa Multi-Titolo")

tab1, tab2 = st.tabs(["📊 Screener Automatico Watchlist", "🔍 Dettaglio Singolo Titolo"])

# --- SIDEBAR ---
st.sidebar.header("⚙️ Gestione Rischio & Guadagno")

watchlist_input = st.sidebar.text_area(
    "Inserisci la Watchlist (separata da virgola):",
    value="ANET, CSCO, MRVL, CRDO, CEG, VST, VRT, SU, EQIX, BYDDY, NVO, TSLA"
)

capital = st.sidebar.number_input("Capitale Totale (€/$):", value=10000.0, step=500.0)
max_risk_pct = st.sidebar.slider("Rischio Max per Trade (%):", 0.5, 5.0, 2.0, 0.1)
rr_ratio = st.sidebar.slider("Rapporto Risk/Reward (es. 1:2 o 1:3):", 1.0, 5.0, 2.0, 0.5)

st.sidebar.info("🛡️ **Stop Loss Dinamico:** Calcolato automaticamente su **1.5x ATR** per evitare l'uscita da rumore di mercato.")

st.sidebar.markdown("---")
st.sidebar.header("🔔 Test Notifiche")

if st.sidebar.button("Testa Notifica Telegram"):
    success, error_msg = send_telegram_alert("✅ *Test Riuscito!* Il tuo screener è collegato correttamente a Telegram.")
    if success:
        st.sidebar.success("Notifica inviata con successo!")
    else:
        st.sidebar.error(f"Errore Telegram: {error_msg}")

tickers = [t.strip().upper() for t in watchlist_input.split(",") if t.strip()]

# ==========================================
# TAB 1: SCREENER AUTOMATICO WATCHLIST
# ==========================================
with tab1:
    st.button("🔄 Scansiona Tutta la Watchlist")

    with st.spinner("Caricamento e analisi avanzata in corso..."):
        results = []
        buy_signals = []

        for ticker in tickers:
            data = analyze_ticker(ticker, capital, max_risk_pct, rr_ratio)
            if data:
                results.append(data)
                if data["Decisione Algoritmo"] == "🟢 COMPRA":
                    buy_signals.append(data)

        if results:
            df_results = pd.DataFrame(results)
            st.subheader("Tabella Monitoraggio In Tempo Reale")
            st.dataframe(df_results, use_container_width=True)

            if buy_signals:
                st.success(f"Trovati {len(buy_signals)} segnali COMPRA!")
            else:
                st.info("Nessun titolo della watchlist soddisfa le condizioni di acquisto al momento. L'algoritmo consiglia di attendere.")

# ==========================================
# TAB 2: DETTAGLIO SINGOLO TITOLO (GRAFICO)
# ==========================================
with tab2:
    st.subheader("📊 Analisi Grafica e Dettaglio Singolo Titolo")
    selected_ticker = st.selectbox("Seleziona un titolo da analizzare:", tickers)

    if selected_ticker:
        try:
            df_chart = yf.download(selected_ticker, period="1y", interval="1d", progress=False)
            if not df_chart.empty:
                if isinstance(df_chart.columns, pd.MultiIndex):
                    df_chart = df_chart.xs(selected_ticker, axis=1, level=1)

                chart_close = df_chart['Close']
                sma50_chart = chart_close.rolling(window=50).mean()
                sma200_chart = chart_close.rolling(window=200).mean()

                fig = go.Figure()

                # Candele Giapponesi
                fig.add_trace(go.Candlestick(
                    x=df_chart.index,
                    open=df_chart['Open'],
                    high=df_chart['High'],
                    low=df_chart['Low'],
                    close=df_chart['Close'],
                    name="Prezzo Candele"
                ))

                # SMA 50
                fig.add_trace(go.Scatter(
                    x=df_chart.index, y=sma50_chart, mode="lines", name="SMA 50", line=dict(color="#ff7f0e", width=2)
                ))

                # SMA 200
                fig.add_trace(go.Scatter(
                    x=df_chart.index, y=sma200_chart, mode="lines", name="SMA 200", line=dict(color="#2ca02c", width=2, dash="dot")
                ))

                fig.update_layout(
                    title=f"Grafico Candlestick, SMA 50 e SMA 200 — {selected_ticker}",
                    xaxis_title="Data",
                    yaxis_title="Prezzo ($)",
                    template="plotly_dark",
                    height=550,
                    xaxis_rangeslider_visible=False
                )

                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning(f"Impossibile caricare il grafico per {selected_ticker}: {e}")
