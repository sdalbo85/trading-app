import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="Screener e Analizzatore di Borsa", page_icon="📈", layout="wide")

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def generate_signals(df):
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['RSI'] = calculate_rsi(df['Close'])

    df['Signal'] = 'HOLD'
    
    # Condizione BUY: Prezzo sopra SMA50 AND RSI < 45 AND RSI in salita
    buy_cond = (df['Close'] > df['SMA_50']) & (df['RSI'] < 45) & (df['RSI'] > df['RSI'].shift(1))
    # Condizione SELL: Prezzo sotto SMA50 OR RSI > 70
    sell_cond = (df['Close'] < df['SMA_50']) | (df['RSI'] > 70)
    
    df.loc[buy_cond, 'Signal'] = 'BUY'
    df.loc[sell_cond, 'Signal'] = 'SELL'
    
    return df

st.title("📈 Screener e Analizzatore di Borsa Multi-Titolo")

st.sidebar.header("⚙️ Configurazione Watchlist")
default_tickers = "ANET, CSCO, MRVL, CRDO, CEG, VST, VRT, SU, EQIX, BYDDY, NVO, TSLA"
watchlist_input = st.sidebar.text_area("Inserisci la tua Watchlist (separata da virgola):", value=default_tickers, height=120)

# Pulisce la lista dei ticker
ticker_list = [t.strip().upper() for t in watchlist_input.split(",") if t.strip()]

period = st.sidebar.selectbox("Periodo Storico:", ["6m", "1y", "2y", "5y"], index=1)

st.sidebar.subheader("🛡️ Gestione Rischio & Guadagno")
capital = st.sidebar.number_input("Capitale Totale (€/$):", min_value=100.0, value=10000.0, step=500.0)
risk_per_trade_pct = st.sidebar.slider("Rischio Max (%):", 0.5, 5.0, 2.0, 0.5)
stop_loss_pct = st.sidebar.slider("Stop Loss (%):", 1.0, 10.0, 3.0, 0.5)

# NUOVO PARAMETRO: Take Profit Target
rr_ratio = st.sidebar.slider("Rapporto Risk/Reward (es. 1:2 o 1:3):", 1.0, 5.0, 2.0, 0.5)
take_profit_pct = stop_loss_pct * rr_ratio

st.sidebar.info(f"🎯 **Target Take Profit:** +{take_profit_pct:.1f}% dal prezzo di acquisto")

estimated_spread = st.sidebar.number_input("Spread Stimato (€/$):", min_value=0.00, value=0.05, step=0.01)

tab1, tab2 = st.tabs(["📊 Screener Automatico Watchlist", "🔍 Dettaglio Singolo Titolo"])

# ---------------------------------------------------------
# TAB 1: SCREENER MULTI-TITOLO (DOWNLOAD BATCH OTTIMIZZATO)
# ---------------------------------------------------------
with tab1:
    st.subheader("Tabella Monitoraggio In Tempo Reale")
    if st.button("🔄 Scansiona Tutta la Watchlist"):
        st.cache_data.clear()
    
    results = []
    
    if ticker_list:
        with st.spinner("Scaricamento dati veloce in corso..."):
            try:
                batch_data = yf.download(ticker_list, period=period, interval="1d", group_by='ticker', progress=False)
                
                for ticker in ticker_list:
                    try:
                        if len(ticker_list) == 1:
                            df_single = batch_data.copy()
                        else:
                            df_single = batch_data[ticker].dropna(how="all")
                        
                        if isinstance(df_single.columns, pd.MultiIndex):
                            df_single.columns = df_single.columns.get_level_values(0)
                        
                        if not df_single.empty and 'Close' in df_single.columns and len(df_single) > 50:
                            df_single = generate_signals(df_single)
                            last_row = df_single.iloc[-1]
                            
                            status = "⚪ ATTENDI"
                            if last_row['Signal'] == 'BUY':
                                status = "🟢 COMPRA"
                            elif last_row['Signal'] == 'SELL':
                                status = "🔴 VENDI / FUORI"
                            
                            eff_price = last_row['Close'] + estimated_spread
                            max_risk = capital * (risk_per_trade_pct / 100.0)
                            loss_per_sh = eff_price * (stop_loss_pct / 100.0)
                            shares = int(max_risk / loss_per_sh) if loss_per_sh > 0 else 0
                            
                            # Calcolo Prezzi Target
                            sl_price = eff_price * (1 - (stop_loss_pct / 100.0))
                            tp_price = eff_price * (1 + (take_profit_pct / 100.0))
                            
                            results.append({
                                "Ticker": ticker,
                                "Prezzo ($/€)": round(float(last_row['Close']), 2),
                                "Decisione Algoritmo": status,
                                "RSI (14)": round(float(last_row['RSI']), 1),
                                "Sopra SMA50": "Sì" if last_row['Close'] > last_row['SMA_50'] else "No",
                                "Azioni Consigliate": shares if last_row['Signal'] == 'BUY' else 0,
                                "Stop Loss Target ($)": round(sl_price, 2) if last_row['Signal'] == 'BUY' else 0,
                                "Take Profit Target ($)": round(tp_price, 2) if last_row['Signal'] == 'BUY' else 0,
                                "Capitale Richiesto ($/€)": round(shares * eff_price, 2) if last_row['Signal'] == 'BUY' else 0
                            })
                    except Exception:
                        continue
            except Exception as e:
                st.error("Errore temporaneo nel recupero dati dai mercati. Riprova tra poco.")

    if results:
        res_df = pd.DataFrame(results)
        
        st.dataframe(
            res_df.style.map(
                lambda v: 'background-color: #1e4620; color: white' if 'COMPRA' in str(v) else ('background-color: #4a1c1d; color: white' if 'VENDI' in str(v) else ''),
                subset=['Decisione Algoritmo']
            ),
            use_container_width=True
        )
        
        buy_opportunities = res_df[res_df['Decisione Algoritmo'] == "🟢 COMPRA"]
        if not buy_opportunities.empty:
            st.success(f"🎯 **Trovate {len(buy_opportunities)} opportunità di acquisto!**")
            st.table(buy_opportunities[['Ticker', 'Prezzo ($/€)', 'Azioni Consigliate', 'Stop Loss Target ($)', 'Take Profit Target ($)', 'Capitale Richiesto ($/€)']])
        else:
            st.info("Nessun titolo della watchlist soddisfa le condizioni di acquisto al momento. L'algoritmo consiglia di attendere.")

# ---------------------------------------------------------
# TAB 2: DETTAGLIO SINGOLO TITOLO
# ---------------------------------------------------------
with tab2:
    st.subheader("Analisi Grafica del Titolo")
    
    col_sel, col_manual = st.columns([2, 1])
    with col_sel:
        selected_ticker = st.selectbox("Seleziona dalla tua Watchlist:", options=ticker_list, index=0)
    with col_manual:
        manual_ticker = st.text_input("Oppure digita un Ticker manuale:", value="").upper().strip()
    
    active_ticker = manual_ticker if manual_ticker else selected_ticker

    if active_ticker:
        with st.spinner(f"Caricamento grafico per {active_ticker}..."):
            try:
                data = yf.download(active_ticker, period=period, interval="1d", progress=False)
                if isinstance(data.columns, pd.MultiIndex):
                    data.columns = data.columns.get_level_values(0)
                    
                if not data.empty and 'Close' in data.columns and len(data) > 50:
                    df = generate_signals(data)
                    last_row = df.iloc[-1]
                    
                    c_m1, c_m2, c_m3 = st.columns(3)
                    c_m1.metric("Titolo", active_ticker)
                    c_m2.metric("Prezzo Attuale", f"{last_row['Close']:.2f} $")
                    
                    sig_label = "⚪ ATTENDI (HOLD)"
                    if last_row['Signal'] == 'BUY':
                        sig_label = "🟢 COMPRA ORA"
                    elif last_row['Signal'] == 'SELL':
                        sig_label = "🔴 VENDI / FUORI"
                    c_m3.metric("Decisione Algoritmo", sig_label)
                    
                    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
                    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Candele"), row=1, col=1)
                    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], line=dict(color='blue', width=1), name="SMA 20g"), row=1, col=1)
                    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], line=dict(color='orange', width=1.5), name="SMA 50g"), row=1, col=1)
                    
                    buy_signals = df[df['Signal'] == 'BUY']
                    fig.add_trace(go.Scatter(x=buy_signals.index, y=buy_signals['Low'] * 0.98, mode='markers', marker=dict(symbol='triangle-up', size=12, color='green'), name="Compra"), row=1, col=1)
                    
                    sell_signals = df[df['Signal'] == 'SELL']
                    fig.add_trace(go.Scatter(x=sell_signals.index, y=sell_signals['High'] * 1.02, mode='markers', marker=dict(symbol='triangle-down', size=12, color='red'), name="Vendi"), row=1, col=1)
                    
                    fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], line=dict(color='purple', width=1.5), name="RSI"), row=2, col=1)
                    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
                    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
                    fig.update_layout(xaxis_rangeslider_visible=False, height=500, margin=dict(l=20, r=20, t=20, b=20))
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.error(f"Impossibile recuperare i dati per '{active_ticker}'. Verificare il codice ticker.")
            except Exception:
                st.error("Si è verificato un errore durante il caricamento del grafico.")
