import yfinance as yf
import pandas as pd
import streamlit as st


@st.cache_data
def load_market_data() -> pd.DataFrame:
    tickers = {
        "Bitcoin": "BTC-USD", "Ethereum": "ETH-USD", "Solana": "SOL-USD",
        "CAC40": "^FCHI", "S&P500": "^GSPC", "Apple": "AAPL",
        "Google": "GOOGL", "LVMH": "MC.PA", "Or": "GC=F", "Argent": "SI=F"
    }
    data = yf.download(list(tickers.values()), period="5y")["Close"]
    data.columns = tickers.keys()
    return data.ffill().dropna(axis=1, how="all")
