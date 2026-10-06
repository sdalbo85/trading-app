import yfinance as yf
import pandas as pd
import requests

TELEGRAM_TOKEN = "8880305168:AAEwG78l80y4H0wwgy18byQ6swNSo-XxLJY"
TELEGRAM_CHAT_ID = "8821873237"

WATCHLIST = ["ANET", "CSCO", "MRVL", "CRDO", "CEG", "VST", "VRT", "SU", "EQIX", "BYDDY", "NVO", "TSLA"]
CAPITAL = 10000.0
MAX_RISK_PCT = 2.0
STOP_LOSS_PCT = 3.0
RR_RATIO = 2.0

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Errore invio: {e}")

def calculate_rsi(data, period=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def run_scan():
    for ticker in WATCHLIST:
        try:
            df = yf.download(ticker, period="1y", interval="1d", progress=False)
            if df.empty:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df = df.xs(ticker, axis=1, level=1)

            close = df['Close']
            sma_50 = close.rolling(window=50).mean()
            rsi = calculate_rsi(close, period=14)

            current_price = float(close.iloc[-1])
            current_sma = float(sma_50.iloc[-1])
            current_rsi = float(rsi.iloc[-1])

            # Condizione d'acquisto
            if current_price > current_sma and current_rsi < 45:
                max_risk_amount = CAPITAL * (MAX_RISK_PCT / 100.0)
                sl_target = current_price * (1 - (STOP_LOSS_PCT / 100.0))
                tp_pct = STOP_LOSS_PCT * RR_RATIO
                tp_target = current_price * (1 + (tp_pct / 100.0))
                
                risk_per_share = current_price - sl_target
                shares = int(max_risk_amount / risk_per_share) if risk_per_share > 0 else 0
                req_capital = shares * current_price

                msg = (
                    f"🚨 *SEGNALE DI ACQUISTO AUTOMATICO!* 🚨\n\n"
                    f"📈 *Ticker:* {ticker}\n"
                    f"💰 *Prezzo Attuale:* ${current_price:.2f}\n"
                    f"📊 *RSI:* {current_rsi:.2f}\n\n"
                    f"📦 *Azioni Consigliate:* {shares}\n"
                    f"🛑 *Stop Loss Target:* ${sl_target:.2f}\n"
                    f"🎯 *Take Profit Target:* ${tp_target:.2f}\n"
                    f"💵 *Capitale Richiesto:* ${req_capital:.2f}\n\n"
                    f"⚡ *Azione:* Apri TradingView ed esegui l'ordine!"
                )
                send_telegram_alert(msg)
        except Exception as e:
            print(f"Errore su {ticker}: {e}")

if __name__ == "__main__":
    run_scan()
