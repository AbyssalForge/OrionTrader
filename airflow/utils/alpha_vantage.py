import requests
import pandas as pd
from utils.vault_helper import get_vault

vault = get_vault()

BASE_URL = vault.get_secret("AlphaVantage", "BASE_URL")
API_KEY = vault.get_secret("AlphaVantage", "API_KEY")


# EUR / USD – Forex intraday (15 minutes)
def get_eurusd_intraday_15min(outputsize: str = "full") -> pd.DataFrame:
    """
    Récupère EUR/USD en 15 minutes via Alpha Vantage
    Source externe (confirmation), pas remplacement MT5
    """
    params = {
        "function": "FX_INTRADAY",
        "from_symbol": "EUR",
        "to_symbol": "USD",
        "interval": "15min",
        "outputsize": outputsize,
        "apikey": API_KEY,
    }

    r = requests.get(BASE_URL, params=params, timeout=30)
    r.raise_for_status()

    data = r.json().get("Time Series FX (15min)", {})
    if not data:
        raise ValueError("Aucune donnée EUR/USD retournée par l'API")

    df = pd.DataFrame(data).T.astype(float)
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    df.columns = ["open_api", "high_api", "low_api", "close_api"]
    df.index.name = "time"

    return df


# Dollar Index (DXY) – régime dollar
def get_dxy_daily() -> pd.DataFrame:
    """
    Récupère le Dollar Index (DXY) en daily
    """
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": "DTWEXBGS",
        "apikey": API_KEY,
    }

    r = requests.get(BASE_URL, params=params, timeout=30)
    r.raise_for_status()

    data = r.json().get("Time Series (Daily)", {})
    if not data:
        raise ValueError("Aucune donnée DXY retournée par l'API")

    df = pd.DataFrame(data).T.astype(float)
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    df = df[["4. close"]]
    df.columns = ["dxy_close"]
    df.index.name = "time"

    return df


# Taux US 10Y – macro inter-marché
def get_us10y_treasury_yield() -> pd.DataFrame:
    """
    Récupère le taux US 10Y (daily)
    """
    params = {
        "function": "TREASURY_YIELD",
        "interval": "daily",
        "maturity": "10year",
        "apikey": API_KEY,
    }

    r = requests.get(BASE_URL, params=params, timeout=30)
    r.raise_for_status()

    data = r.json().get("data", [])
    if not data:
        raise ValueError("Aucune donnée de taux US 10Y retournée")

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = df["value"].astype(float)

    df = df.set_index("date").sort_index()
    df.columns = ["us10y_yield"]
    df.index.name = "time"

    return df


# VIX – stress global du marché
def get_vix_daily() -> pd.DataFrame:
    """
    Récupère le VIX en daily
    """
    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": "VIX",
        "apikey": API_KEY,
    }

    r = requests.get(BASE_URL, params=params, timeout=30)
    r.raise_for_status()

    data = r.json().get("Time Series (Daily)", {})
    if not data:
        raise ValueError("Aucune donnée VIX retournée par l'API")

    df = pd.DataFrame(data).T.astype(float)
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    df = df[["4. close"]]
    df.columns = ["vix_close"]
    df.index.name = "time"

    return df


# Harmonisation temporelle (M15)
def resample_to_15min(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aligne une série daily sur du M15 par forward-fill contrôlé
    """
    return df.resample("15T").ffill()