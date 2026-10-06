import streamlit as st
import yfinance as yf
import pandas as pd
import requests

# ==========================================
# 1. CONFIGURAZIONE TELEGRAM
# ==========================================
# Sostituisci queste stringhe con i tuoi dati reali
TELEGRAM_TOKEN = "8880305168:AAEwG78l80y4H0wwgy18byQ6swNSo-XxLJY"
TELEGRAM_CHAT_ID = "8821873237"

def send_telegram_alert(message):
    """Invia un messaggio formattato al bot Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Errore invio Telegram: {e}")
        return False

# ==========================================
# 2. FUNZIONI CALCOLO INDICATORI
# ==========================================
def calculate_rsi(data, period=14):
    """Calcola l'RSI a 14 periodi."""
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def analyze_ticker(ticker, capital, max_risk_pct, stop_loss_pct, rr_ratio):
    """Scarica i dati ed esegue l'analisi del segnale e della gestione rischio."""
    try:
        df = yf.download(ticker, period="1y", interval="1d", progress=False)
        if df.empty:
            return None
        
        # Gestione colonne MultiIndex di yfinance
        if isinstance(df.columns, pd.MultiIndex):
            df = df.xs(ticker, axis=1, level=1)

        close = df['Close']
        sma_50 = close.rolling(window=50).mean()
        rsi = calculate_rsi(close, period=14)

        current_price = float(close.iloc[-1])
        current_sma = float(sma_50.iloc[-1])
        current_rsi = float(rsi.iloc[-1])

        # Logica del Segnale
        if current_price > current_sma and current_rsi < 45:
            decision = "COMPRA"
        elif current_rsi > 70 or current_price < current_sma:
            decision = "VENDI / FUORI"
        else:
            decision = "ATTENDI"

        # Calcolo Gestione Rischio (solo se COMPRA)
        if decision == "COMPRA":
            max_risk_amount = capital * (max_risk_pct / 100.0)
            sl_target = current_price * (1 - (stop_loss_pct / 100.0))
            tp_pct = stop_loss_pct * rr_ratio
            tp_target = current_price * (1 + (tp_pct / 100.0))
            
            risk_per_share = current_price - sl_target
            shares = int(max_risk_amount / risk_per_share) if risk_per_share > 0 else 0
            req_capital = shares * current_price
        else:
            shares = 0
            sl_target = 0.0
            tp_target = 0.0
            req_capital = 0.0

        return {
            "Ticker": ticker,
            "Prezzo ($/€)": current_price,
            "Decisione Algoritmo": decision,
            "RSI (14)": current_rsi,
            "Sopra SMA50": "Sì" if current_price > current_sma else "No",
            "Azioni Consigliate": shares,
            "Stop Loss Target ($)": sl_target,
            "Take Profit Target ($)": tp_target,
            "Capitale Richiesto ($/€)": req_capital
        }
    except Exception as e:
        st.error(f"Errore nell'analisi di {ticker}: {e}")
        return None

# ==========================================
# 3. INTERFACCIA UTENTE STREAMLIT
# ==========================================
st.set_page_config(page_title="Screener & Analizzatore Borsa", layout="wide")
st.title("📈 Screener e Analizzatore di Borsa Multi-Titolo")

# --- SIDEBAR: PARAMETRI ---
st.sidebar.header("⚙️ Gestione Rischio & Guadagno")

watchlist_input = st.sidebar.text_area(
    "Inserisci la Watchlist (separata da virgola):",
    value="ANET, CSCO, MRVL, CRDO, CEG, VST, VRT, SU, EQIX, BYDDY, NVO, TSLA"
)

capital = st.sidebar.number_input("Capitale Totale (€/$):", value=10000.0, step=500.0)
max_risk_pct = st.sidebar.slider("Rischio Max (%):", 0.5, 5.0, 2.0, 0.1)
stop_loss_pct = st.sidebar.slider("Stop Loss (%):", 1.0, 10.0, 3.0, 0.5)
rr_ratio = st.sidebar.slider("Rapporto Risk/Reward (es. 1:2 o 1:3):", 1.0, 5.0, 2.0, 0.5)

st.sidebar.markdown("---")
st.sidebar.header("🔔 Test Notifiche")

if st.sidebar.button("Testa Notifica Telegram"):
    success = send_telegram_alert("✅ *Test Riuscito!* Il tuo screener è collegato correttamente a Telegram.")
    if success:
        st.sidebar.success("Notifica inviata con successo sul telefono!")
    else:
        st.sidebar.error("Errore invio. Controlla Token e Chat ID.")

# --- SCANNER PRINCIPALE ---
tickers = [t.strip().upper() for t in watchlist_input.split(",") if t.strip()]

if st.button("🔄 Scansiona Tutta la Watchlist"):
    st.info("Scansione in corso...")
    results = []
    buy_signals = []

    for ticker in tickers:
        data = analyze_ticker(ticker, capital, max_risk_pct, stop_loss_pct, rr_ratio)
        if data:
            results.append(data)
            if data["Decisione Algoritmo"] == "COMPRA":
                buy_signals.append(data)

    if results:
        df_results = pd.DataFrame(results)
        st.subheader("Tabella Monitoraggio In Tempo Reale")
        st.dataframe(df_results, use_container_width=True)

        # Invia notifiche Telegram se ci sono segnali d'acquisto
        if buy_signals:
            for item in buy_signals:
                msg = (
                    f"🚨 *SEGNALE DI ACQUISTO DETECTED!* 🚨\n\n"
                    f"📈 *Ticker:* {item['Ticker']}\n"
                    f"💰 *Prezzo:* ${item['Prezzo ($/€)']:.2f}\n"
                    f"📊 *RSI:* {item['RSI (14)']:.2f}\n\n"
                    f"📦 *Azioni Consigliate:* {item['Azioni Consigliate']}\n"
                    f"🛑 *Stop Loss Target:* ${item['Stop Loss Target ($)']:.2f}\n"
                    f"🎯 *Take Profit Target:* ${item['Take Profit Target ($)']:.2f}\n"
                    f"💵 *Capitale Richiesto:* ${item['Capitale Richiesto ($/€)']:.2f}\n\n"
                    f"⚡ *Azione:* Apri TradingView ed esegui l'ordine!"
                )
                send_telegram_alert(msg)
            st.success(f"Trovati {len(buy_signals)} segnali COMPRA! Notifiche inviate su Telegram.")
        else:
            st.warning("Nessun titolo della watchlist soddisfa le condizioni di acquisto al momento.")
