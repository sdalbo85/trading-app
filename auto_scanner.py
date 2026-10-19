import os
import requests
import yfinance as yf
import pandas as pd

# ==========================================
# CONFIGURAZIONE & PARAMETRI
# ==========================================
TELEGRAM_TOKEN = "8880305168:AAEwG78l80y4HOwwgy18byQ6swNSo-XxlJY"
TELEGRAM_CHAT_ID = "8821873237"

WATCHLIST = [
    "NVDA", "AMD", "AVGO", "ARM", "PLTR", "PANW", "CRWD", "NET", 
    "VST", "CEG", "VRT", "ANET", "AMZN", "SHOP", "MELI", "CELH", 
    "COIN", "UBER", "PYPL", "TSLA"
]

CAPITAL = 1000.0        # Adattato al capitale reale di 1.000€
MAX_RISK_PCT = 2.0     # Rischio massimo per trade (2% = 20€)
RR_RATIO = 2.0         # Risk/Reward Ratio (1:2)

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
    print("🚀 Avvio scansione ottimizzata con filtri di inversione...")
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
            prev_price = float(close.iloc[-2])
            
            current_sma50 = float(sma_50.iloc[-1])
            current_sma200 = float(sma_200.iloc[-1])
            
            current_rsi = float(rsi.iloc[-1])
            prev_rsi = float(rsi.iloc[-2])
            
            current_vol = float(volume.iloc[-1])
            avg_vol = float(vol_sma_20.iloc[-1])
            current_atr = float(atr.iloc[-1])

            # ==========================================
            # LOGICA DI INGRESSO RIGIDA (FILTRI ANTI-PERDITA)
            # ==========================================
            # 1. Trend di medio: Prezzo > SMA 50
            # 2. Pullback contenuto: RSI < 48
            # 3. CONFERMA INVERSIONE RSI: RSI oggi > RSI ieri (momentum rialzista)
            # 4. CONFERMA CANDELA: Prezzo oggi > Prezzo ieri
            
            cond_trend = current_price > current_sma50
            cond_pullback = current_rsi < 48
            cond_rsi_rebound = current_rsi > prev_rsi
            cond_price_rebound = current_price > prev_price

            if cond_trend and cond_pullback and cond_rsi_rebound and cond_price_rebound:
                # Rating di qualità
                rating_score = 2
                if current_price > current_sma200:
                    rating_score += 1
                if current_vol > avg_vol:
                    rating_score += 1
                stars = "⭐" * rating_score

                # Risk Management (2.0x ATR per resistere al rumore)
                max_risk_amount = CAPITAL * (MAX_RISK_PCT / 100.0) # 20€ su 1.000€
                sl_distance = current_atr * 2.0
                sl_target = current_price - sl_distance
                tp_target = current_price + (sl_distance * RR_RATIO)
                
                shares = int(max_risk_amount / sl_distance) if sl_distance > 0 else 0
                if shares < 1:
                    shares = 1 # Garanzia min 1 azione per conti ridotti

                forza_vol = "🔥 Alti" if current_vol > avg_vol else "❄️ Normali"
                sopra_200 = "Sì" if current_price > current_sma200 else "No"

                msg = (
                    f"🟢 **SEGNALE COMPRA OTTIMIZZATO: {ticker}**\n\n"
                    f"Qualità: {stars} ({rating_score}/4)\n"
                    f"Prezzo di Ingresso: ${current_price:.2f}\n"
                    f"RSI (14): {current_rsi:.1f} (Inversione dal precedente {prev_rsi:.1f})\n"
                    f"Stop Loss (2.0x ATR): ${sl_target:.2f}\n"
                    f"Take Profit Target: ${tp_target:.2f}\n"
                    f"Azioni da Comprare: {shares} (Rischio Max: ~${max_risk_amount:.0f})\n"
                    f"Volumi: {forza_vol} | Sopra SMA200: {sopra_200}"
                )
                
                send_telegram_alert(msg)
                buy_signals.append(ticker)
                print(f"✅ Segnale filtrato inviato per {ticker}")

        except Exception as e:
            print(f"Errore scansione {ticker}: {e}")

    print(f"🏁 Scansione completata. Trovati {len(buy_signals)} segnali filtrati.")

if __name__ == "__main__":
    run_scanner()
