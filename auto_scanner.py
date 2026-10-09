import yfinance as yf
import pandas as pd
import requests
import os
from datetime import datetime

TELEGRAM_TOKEN = "8880305168:AAEwG78l80y4HOwwgy18byQ6swNSo-XxlJY" 
TELEGRAM_CHAT_ID = "8821873237"

WATCHLIST = ["SU", "PLTR", "AMD", "NET", "COIN", "ARM", "CELH", "SHOP", "UBER", "PATH", "PANW", "ANET", "CSCO", "MRVL", "CRDO", "CEG", "VST", "EQUIX", "NVO", "TSLA"]
CAPITAL = 10000.0
MAX_RISK_PCT = 2.0
STOP_LOSS_PCT = 3.0
RR_RATIO = 2.0

LOG_FILE = "trading_log.csv"

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

def log_trade(ticker, price, rsi, vol_status, sl, tp, shares, capital_req):
    file_exists = os.path.isfile(LOG_FILE)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    df_new = pd.DataFrame([{
        "Data_Ora": now_str,
        "Ticker": ticker,
        "Prezzo": round(price, 2),
        "RSI": round(rsi, 2),
        "Forza_Volumi": vol_status,
        "Stop_Loss": round(sl, 2),
        "Take_Profit": round(tp, 2),
        "Azioni": shares,
        "Capitale_Richiesto": round(capital_req, 2)
    }])
    
    if not file_exists:
        df_new.to_csv(LOG_FILE, index=False)
    else:
        df_new.to_csv(LOG_FILE, mode='a', header=False, index=False)

def run_scan():
    for ticker in WATCHLIST:
        try:
            df = yf.download(ticker, period="1y", interval="1d", progress=False)
            if df.empty:
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df = df.xs(ticker, axis=1, level=1)

            close = df['Close']
            volume = df['Volume']
            
            sma_50 = close.rolling(window=50).mean()
            vol_sma_20 = volume.rolling(window=20).mean()
            rsi = calculate_rsi(close, period=14)

            current_price = float(close.iloc[-1])
            current_sma = float(sma_50.iloc[-1])
            current_rsi = float(rsi.iloc[-1])
            current_vol = float(volume.iloc[-1])
            avg_vol = float(vol_sma_20.iloc[-1])

            # Condizione d'acquisto principale (Non si perde nessun segnale)
            if current_price > current_sma and current_rsi < 45:
                max_risk_amount = CAPITAL * (MAX_RISK_PCT / 100.0)
                sl_target = current_price * (1 - (STOP_LOSS_PCT / 100.0))
                tp_pct = STOP_LOSS_PCT * RR_RATIO
                tp_target = current_price * (1 + (tp_pct / 100.0))
                
                risk_per_share = current_price - sl_target
                shares = int(max_risk_amount / risk_per_share) if risk_per_share > 0 else 0
                req_capital = shares * current_price

                # Valutazione informativa della forza dei volumi
                vol_status = "ALTI" if current_vol > avg_vol else "STANDBY"
                vol_badge = "🔥 ALTI (Sopra la media 20gg)" if vol_status == "ALTI" else "❄️ STANDBY / MEDI"

                # 1. Notifica Telegram con indicatore volumi
                msg = (
                    f"🚨 *SEGNALE DI ACQUISTO DETECTED!* 🚨\n\n"
                    f"📈 *Ticker:* {ticker}\n"
                    f"💰 *Prezzo Attuale:* ${current_price:.2f}\n"
                    f"📊 *RSI:* {current_rsi:.2f}\n"
                    f"⚡ *Forza Volumi:* {vol_badge}\n\n"
                    f"📦 *Azioni Consigliate:* {shares}\n"
                    f"🛑 *Stop Loss Target:* ${sl_target:.2f}\n"
                    f"🎯 *Take Profit Target:* ${tp_target:.2f}\n"
                    f"💵 *Capitale Richiesto:* ${req_capital:.2f}\n\n"
                    f"📲 *Azione:* Apri TradingView e valuta l'ordine!"
                )
                send_telegram_alert(msg)

                # 2. Salva lo storico nel CSV
                log_trade(ticker, current_price, current_rsi, vol_status, sl_target, tp_target, shares, req_capital)

        except Exception as e:
            print(f"Errore su {ticker}: {e}")

if __name__ == "__main__":
    run_scan()
