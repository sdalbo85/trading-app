import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Trading Screener Test", layout="wide")
st.title("Trading Screener - Reset Test")

# Test minimale per 3 titoli
tickers = ["TSLA", "AAPL", "NVDA"]

if st.button("🔄 Avvia Test Download"):
    st.write("Scaricamento in corso...")
    try:
        data = yf.download(tickers, period="1mo")
        st.write("Dati scaricati con successo!")
        st.dataframe(data["Close"])
    except Exception as e:
        st.error(f"Errore: {e}")
