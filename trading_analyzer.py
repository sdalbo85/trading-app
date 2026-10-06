import streamlit as st
import yfinance as yf
import pandas as pd
import requests

# ==========================================
# 1. CONFIGURAZIONE TELEGRAM
# ==========================================
TELEGRAM_TOKEN = "8880305168:AAEwG78l80y4H0wwgy18byQ6swNSo-XxLJY"
TELEGRAM_CHAT_ID = "8821873237"

def send_telegram_alert(message):
    """Invia un messaggio formattato al bot Telegram e mostra l'errore reale se fallisce."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        res_data = response.json()
        if response.status_code == 200:
            return True, "OK"
        else:
            # Restituisce il motivo esatto specificato dai server di Telegram
            return False, res_data.get("description", "Errore sconosciuto da Telegram")
    except Exception as e:
        return False, str(e)

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

        # Logica del Segnale con Icone Colorate
        if current_price > current_sma and current_rsi < 45:
            decision = "🟢 COMPRA"
        elif current_rsi > 70 or current_price < current_sma:
            decision = "🔴 VENDI / FUORI"
        else:
            decision = "⚪ ATTENDI"

        # Calcolo Gestione Rischio (solo se COMPRA)
        if decision == "🟢 COMPRA":
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
st.set_page_config(page_title="Screener & Analizzatore Borsa",
