import yfinance as yf
import pandas as pd
from prefect import get_run_logger

def import_data():
    try:
        df = yf.download("EURUSD=X", start="2020-01-01", end="2025-10-01", interval="1d")
    except Exception as e:
        return pd.DataFrame()

    df = df[['Open', 'High', 'Low', 'Close']].dropna().reset_index(drop=True)

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0].lower() for col in df.columns]
    else:
        df.columns = df.columns.str.lower()

    return df
