import streamlit as st
import auto_scanner

st.set_page_config(page_title="Screener Quantitativo", layout="wide")

st.title("📊 Screener Quantitativo & Trading System")
st.markdown("Sistema automatico per swing trading basato su Trend, RSI, ATR e Volumi.")

st.sidebar.header("⚙️ Configurazione & Parametri")
st.sidebar.info("La logica e i filtri (2.0x ATR, Inversione RSI) sono sincronizzati con auto_scanner.py.")

if st.sidebar.button("🧪 Invia Test Telegram"):
    ok = auto_scanner.send_telegram_alert("✅ **Test Telegram Streamlit:** Connessione riuscita!")
    if ok:
        st.sidebar.success("Messaggio inviato!")
    else:
        st.sidebar.error("Errore invio Telegram")

if st.sidebar.button("🔄 Avvia Scansione Manuale"):
    st.cache_data.clear()
    st.rerun()

with st.spinner("Scansione della Watchlist in corso..."):
    df_results = auto_scanner.get_screener_dataframe()

if not df_results.empty:
    st.subheader("📋 Watchlist e Segnali in Tempo Reale")
    st.dataframe(df_results, use_container_width=True)
else:
    st.warning("Nessun dato disponibile o errore durante lo scaricamento.")
