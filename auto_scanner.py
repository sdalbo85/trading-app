import os
import requests
import yfinance as yf
import pandas as pd

TELEGRAM_TOKEN = "8880305168:AAEwG78l80y4HOwwgy18byQ6swNSo-XxlJY"
TELEGRAM_CHAT_ID = "8821873237"

WATCHLIST = [
    "NVDA", "AMD", "AVGO", "ARM", "PLTR", "PANW", "CRWD", "NET", 
    "VST", "CEG", "VRT", "ANET", "AMZN", "SHOP", "MELI", "CELH", 
    "COIN", "UBER", "PYPL", "TSLA", "SU", "XOM", "CVX", "CAT", 
    "LLY", "NVO", "COST", "WMT", "JPM", "LMT"
]

CAPITAL = 5000.0
MAX_RISK_PCT = 2.0
RR_RATIO = 2.0

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        res = requests.post(url, json=payload, timeout=10)
        return res.status_code == 200
    except Exception as e:
        print(f"Errore Telegram: {e}")
        return False

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

def run_scanner():
    print("Avvio scansione mercato...")
    for ticker in WATCHLIST:
        try:
            df = yf.download(ticker, period="1y", interval="1d", progress=False)
            if df.empty or len(df) < 50:
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
            current_sma50 = float(sma_50.iloc[-1]) if not pd.isna(sma_50.iloc[-1]) else current_price
            current_sma200 = float(sma_200.iloc[-1]) if not pd.isna(sma_200.iloc[-1]) else current_price
            current_rsi = float(rsi.iloc[-1])
            prev_rsi = float(rsi.iloc[-2])
            current_vol = float(volume.iloc[-1])
            avg_vol = float(vol_sma_20.iloc[-1]) if not pd.isna(vol_sma_20.iloc[-1]) else current_vol
            current_atr = float(atr.iloc[-1]) if not pd.isna(atr.iloc[-1]) else current_price * 0.02

            # Filtri d'ingresso
            cond_trend = current_price > current_sma50
            cond_pullback = current_rsi < 48
            cond_rsi_rebound = current_rsi > prev_rsi
            cond_price_rebound = current_price > prev_price

            if cond_trend and cond_pullback and cond_rsi_rebound and cond_price_rebound:
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
                
                shares = int(max_risk_amount / sl_distance) if sl_distance > 0 else 1

                msg = (
                    f"🟢 **SEGNALE COMPRA OTTIMIZZATO: {ticker}**\n\n"
                    f"Qualità: {stars}\n"
                    f"Prezzo di Ingresso: ${current_price:.2f}\n"
                    f"RSI (14): {current_rsi:.1f}\n"
                    f"Stop Loss (2.0x ATR): ${sl_target:.2f}\n"
                    f"Take Profit Target: ${tp_target:.2f}\n"
                    f"Azioni consigliate: {shares}"
                )
                print(f"Segnale trovato per {ticker}! Invio notifica...")
                send_telegram_alert(msg)
        except Exception as e:
            print(f"Errore su {ticker}: {e}")
            continue

    print("Scansione completata.")

if __name__ == "__main__":
    run_scanner()
