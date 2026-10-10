import os
import requests
import yfinance as yf
import pandas as pd

# ==========================================
# CONFIGURAZIONE & PARAMETRI
# ==========================================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "8880305168:AAEwG78l80y4HOwwgy18byQ6swNSo-XxlJY")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "8821873237")

WATCHLIST = [“NVDA”, “AMD”, “AVGO”, “ARM”, “PLTR”, “PANW”, “CRWD”, “NET”, “VST”, “CEG”, “VRT”, “ANET”, “AMZN”, “SHOP”, “MELI”, “CELH”, “COIN”, “UBER”, “PYPL”, “TSLA”]

CAPITAL = 10000.0
MAX_RISK_PCT = 2.0
RR_RATIO = 2.0

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Errore invio Telegram: {e}")
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
    print("🚀 Avvio scansione automatica mercato...")
    buy_signals = []

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
            current_sma50 = float(sma_50.iloc[-1])
            current_sma200 = float(sma_200.iloc[-1])
            current_rsi = float(rsi.iloc[-1])
            current_vol = float(volume.iloc[-1])
            avg_vol = float(vol_sma_20.iloc[-1])
            current_atr = float(atr.iloc[-1])

            # Condizione di acquisto
            if current_price > current_sma50 and current_rsi < 45:
                # Rating di qualità
                rating_score = 2
                if current_price > current_sma200:
                    rating_score += 1
                if current_vol > avg_vol:
                    rating_score += 1
                stars = "⭐" * rating_score

                # Risk Management ATR (1.5x ATR)
                max_risk_amount = CAPITAL * (MAX_RISK_PCT / 100.0)
                sl_distance = current_atr * 1.5
                sl_target = current_price - sl_distance
                tp_target = current_price + (sl_distance * RR_RATIO)
                
                shares = int(max_risk_amount / sl_distance) if sl_distance > 0 else 0
                forza_vol = "🔥 Alti" if current_vol > avg_vol else "❄️ Normali"
                sopra_200 = "Sì" if current_price > current_sma200 else "No"

                msg = (
                    f"🟢 **SEGNALE COMPRA: {ticker}**\n\n"
                    f"Qualità: {stars} ({rating_score}/4)\n"
                    f"Prezzo: ${current_price:.2f}\n"
                    f"RSI (14): {current_rsi:.1f}\n"
                    f"Stop Loss (1.5x ATR): ${sl_target:.2f}\n"
                    f"Take Profit Target: ${tp_target:.2f}\n"
                    f"Azioni Consigliate: {shares}\n"
                    f"Volumi: {forza_vol} | Sopra SMA200: {sopra_200}"
                )
                
                send_telegram_alert(msg)
                buy_signals.append(ticker)
                print(f"✅ Segnale inviato per {ticker}")

        except Exception as e:
            print(f"Errore scansione {ticker}: {e}")

    print(f"🏁 Scansione completata. Trovati {len(buy_signals)} segnali.")

if __name__ == "__main__":
    run_scanner()
