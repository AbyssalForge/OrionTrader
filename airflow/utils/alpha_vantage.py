import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from utils.vault_helper import get_vault

vault = get_vault()

BASE_URL = vault.get_secret("AlphaVantage", "BASE_URL")
API_KEY = vault.get_secret("AlphaVantage", "API_KEY")

# URL de Stooq pour les données forex (gratuit, pas besoin d'API key)
STOOQ_BASE_URL = "https://stooq.com/q/d/l/"

# Pour respecter la limite de 1 requête/seconde d'Alpha Vantage
_last_api_call_time = 0
MIN_INTERVAL_BETWEEN_CALLS = 1.2  # 1.2 secondes pour être sûr


def _wait_for_rate_limit():
    """Attend si nécessaire pour respecter la limite de 1 req/sec d'Alpha Vantage"""
    global _last_api_call_time
    current_time = time.time()
    time_since_last_call = current_time - _last_api_call_time

    if time_since_last_call < MIN_INTERVAL_BETWEEN_CALLS:
        wait_time = MIN_INTERVAL_BETWEEN_CALLS - time_since_last_call
        print(f"[RATE LIMIT] Attente de {wait_time:.2f}s pour respecter la limite Alpha Vantage...")
        time.sleep(wait_time)

    _last_api_call_time = time.time()


def _get_stooq_data(symbol: str, days: int = 365, interval: str = 'd') -> pd.DataFrame:
    """
    Fonction générique pour récupérer des données depuis Stooq

    Args:
        symbol: Symbole Stooq (ex: 'eurusd', '^dji', '^vix', 'xauusd')
        days: Nombre de jours d'historique
        interval: Intervalle (d=daily, w=weekly, m=monthly, 5=5min)

    Returns:
        DataFrame avec colonnes standardisées
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")

    url = f"{STOOQ_BASE_URL}?s={symbol}&d1={start_str}&d2={end_str}&i={interval}"

    print(f"[STOOQ] Récupération {symbol} de {start_str} à {end_str} (intervalle: {interval})")
    print(f"[STOOQ] URL: {url}")

    try:
        # Stooq retourne un CSV - lire sans parser les dates d'abord
        df = pd.read_csv(url)

        # Vérifier si le CSV contient des données valides
        if df.empty or 'Date' not in df.columns:
            raise ValueError(f"Symbole {symbol} non disponible ou invalide sur Stooq. Colonnes reçues: {list(df.columns)}")

        # Parser la date après vérification
        df['Date'] = pd.to_datetime(df['Date'])

        # Traiter l'intraday si nécessaire
        if interval in ['5', '15', '30', '60'] and 'Time' in df.columns:
            df['DateTime'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Time'])
            df = df.drop(['Date', 'Time'], axis=1)
            df = df.rename(columns={'DateTime': 'time'})
        else:
            df = df.rename(columns={'Date': 'time'})

        if df.empty:
            raise ValueError(f"Aucune donnée {symbol} retournée par Stooq")

        print(f"[STOOQ] {len(df)} lignes récupérées pour {symbol}")

        # Standardiser les noms de colonnes
        column_mapping = {
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        }
        df = df.rename(columns=column_mapping)

        # Définir time comme index
        df = df.set_index('time').sort_index()

        return df

    except Exception as e:
        raise ValueError(f"Erreur lors de la récupération de {symbol} sur Stooq: {str(e)}")


# ========== FOREX (Daily) - Contexte macro ==========

def get_eurusd_daily_stooq(days: int = 365) -> pd.DataFrame:
    """
    Récupère EUR/USD en daily via Stooq (gratuit, sans API key)
    Contexte: Tendance principale de la paire

    Args:
        days: Nombre de jours d'historique à récupérer (défaut: 365)

    Returns:
        DataFrame avec colonnes: open, high, low, close, volume
    """
    return _get_stooq_data('eurusd', days=days, interval='d')


def get_gbpusd_daily_stooq(days: int = 365) -> pd.DataFrame:
    """
    Récupère GBP/USD en daily via Stooq
    Contexte: Corrélation avec EUR/USD
    """
    return _get_stooq_data('gbpusd', days=days, interval='d')


def get_usdjpy_daily_stooq(days: int = 365) -> pd.DataFrame:
    """
    Récupère USD/JPY en daily via Stooq
    Contexte: Sentiment risk-on/risk-off
    """
    return _get_stooq_data('usdjpy', days=days, interval='d')


# ========== INDICES - Contexte macro ==========

def get_dxy_daily_stooq(days: int = 365) -> pd.DataFrame:
    """
    Récupère le Dollar Index (DXY) en daily via Stooq
    Contexte: Force du dollar US (inverse de EUR/USD)
    Symbole Stooq: usdx (US Dollar Index)
    """
    return _get_stooq_data('usdx', days=days, interval='d')


def get_spx_daily_stooq(days: int = 365) -> pd.DataFrame:
    """
    Récupère le S&P 500 en daily via Stooq
    Contexte: Sentiment général du marché US
    Symbole Stooq: ^spx
    """
    return _get_stooq_data('^spx', days=days, interval='d')


def get_vix_daily_stooq(days: int = 365) -> pd.DataFrame:
    """
    Récupère le VIX (volatilité) en daily via Stooq
    Contexte: Stress et peur sur les marchés
    Symbole Stooq: ^vix
    """
    return _get_stooq_data('^vix', days=days, interval='d')


def get_dji_daily_stooq(days: int = 365) -> pd.DataFrame:
    """
    Récupère le Dow Jones en daily via Stooq
    Contexte: Sentiment marché US (blue chips)
    Symbole Stooq: ^dji
    """
    return _get_stooq_data('^dji', days=days, interval='d')


# ========== COMMODITIES - Or ==========

def get_gold_daily_stooq(days: int = 365) -> pd.DataFrame:
    """
    Récupère l'or (XAU/USD) en daily via Stooq
    Contexte: Valeur refuge, inflation
    Symbole Stooq: xauusd (or vs dollar)
    """
    return _get_stooq_data('xauusd', days=days, interval='d')


def get_silver_daily_stooq(days: int = 365) -> pd.DataFrame:
    """
    Récupère l'argent (XAG/USD) en daily via Stooq
    Contexte: Métaux précieux, corrélation avec or
    """
    return _get_stooq_data('xagusd', days=days, interval='d')


# ========== INTRADAY (optionnel pour vérification) ==========

def get_eurusd_intraday_5min_stooq(days: int = 7) -> pd.DataFrame:
    """
    Récupère EUR/USD en 5 minutes via Stooq (gratuit, sans API key)
    Note: Données intraday limitées aux derniers jours (~7-10)
    Utiliser MT5 comme source principale pour l'intraday

    Args:
        days: Nombre de jours d'historique (max ~7-10 jours)

    Returns:
        DataFrame avec colonnes: open, high, low, close
    """
    return _get_stooq_data('eurusd', days=days, interval='5')


# ========== FONCTION COMPLÈTE - Contexte Macro ==========

def get_macro_context_stooq(days: int = 365) -> dict:
    """
    Récupère l'ensemble du contexte macro via Stooq (GRATUIT)

    Données récupérées:
    - Forex: EUR/USD, GBP/USD, USD/JPY
    - Indices: DXY (Dollar Index), S&P 500, VIX, Dow Jones
    - Commodities: Or (XAU/USD), Argent (XAG/USD)

    Note: Certains actifs peuvent être ignorés s'ils ne sont pas disponibles sur Stooq

    Args:
        days: Nombre de jours d'historique (défaut: 365 = 1 an)

    Returns:
        dict avec toutes les données macro disponibles

    Usage:
        macro = get_macro_context_stooq(days=365)
        df_eurusd = macro.get('eurusd')  # Peut être None si indisponible
        df_vix = macro.get('vix')
    """
    print(f"[STOOQ] Récupération du contexte macro complet ({days} jours)...")

    context = {}
    assets = [
        ('eurusd', 'EUR/USD', get_eurusd_daily_stooq),
        ('gbpusd', 'GBP/USD', get_gbpusd_daily_stooq),
        ('usdjpy', 'USD/JPY', get_usdjpy_daily_stooq),
        ('dxy', 'DXY (Dollar Index)', get_dxy_daily_stooq),
        ('spx', 'S&P 500', get_spx_daily_stooq),
        ('vix', 'VIX', get_vix_daily_stooq),
        ('dji', 'Dow Jones', get_dji_daily_stooq),
        ('gold', 'Or (XAU/USD)', get_gold_daily_stooq),
        ('silver', 'Argent (XAG/USD)', get_silver_daily_stooq),
    ]

    success_count = 0
    failed_assets = []

    for i, (key, name, func) in enumerate(assets, 1):
        try:
            print(f"[STOOQ] {i}/{len(assets)} - {name}...")
            context[key] = func(days)
            success_count += 1
        except Exception as e:
            print(f"[STOOQ] ⚠ {name} non disponible: {str(e)}")
            failed_assets.append(name)
            # Continue avec les autres actifs

    print(f"[STOOQ] ✓ {success_count}/{len(assets)} actifs récupérés avec succès")

    if failed_assets:
        print(f"[STOOQ] ⚠ Actifs non disponibles: {', '.join(failed_assets)}")

    if success_count == 0:
        raise ValueError("Aucun actif n'a pu être récupéré depuis Stooq")

    return context


# Dollar Index (DXY) – régime dollar
def get_dxy_daily(_retry_count: int = 0) -> pd.DataFrame:
    """
    Récupère le Dollar Index (DXY) en daily
    """
    MAX_RETRIES = 3

    _wait_for_rate_limit()

    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": "DTWEXBGS",
        "apikey": API_KEY,
    }

    r = requests.get(BASE_URL, params=params, timeout=30)
    r.raise_for_status()

    response_json = r.json()

    # Vérifier les erreurs API
    if "Information" in response_json:
        info_msg = response_json["Information"]

        if "premium endpoint" in info_msg.lower():
            raise ValueError(f"Endpoint PREMIUM requis. Message: {info_msg}")

        if "rate" in info_msg.lower() or "frequency" in info_msg.lower():
            if _retry_count < MAX_RETRIES:
                print(f"[WARNING] Rate limit. Tentative {_retry_count + 1}/{MAX_RETRIES} dans 2s...")
                time.sleep(2)
                return get_dxy_daily(_retry_count + 1)
            else:
                raise ValueError(f"Rate limit après {MAX_RETRIES} tentatives. Message: {info_msg}")

        raise ValueError(f"Erreur API: {info_msg}")

    data = response_json.get("Time Series (Daily)", {})
    if not data:
        raise ValueError(f"Aucune donnée DXY retournée par l'API. Response: {response_json}")

    df = pd.DataFrame(data).T.astype(float)
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    df = df[["4. close"]]
    df.columns = ["dxy_close"]
    df.index.name = "time"

    return df


# Taux US 10Y – macro inter-marché
def get_us10y_treasury_yield(_retry_count: int = 0) -> pd.DataFrame:
    """
    Récupère le taux US 10Y (daily)
    """
    MAX_RETRIES = 3

    _wait_for_rate_limit()

    params = {
        "function": "TREASURY_YIELD",
        "interval": "daily",
        "maturity": "10year",
        "apikey": API_KEY,
    }

    r = requests.get(BASE_URL, params=params, timeout=30)
    r.raise_for_status()

    response_json = r.json()

    # Vérifier les erreurs API
    if "Information" in response_json:
        info_msg = response_json["Information"]

        if "premium endpoint" in info_msg.lower():
            raise ValueError(f"Endpoint PREMIUM requis. Message: {info_msg}")

        if "rate" in info_msg.lower() or "frequency" in info_msg.lower():
            if _retry_count < MAX_RETRIES:
                print(f"[WARNING] Rate limit. Tentative {_retry_count + 1}/{MAX_RETRIES} dans 2s...")
                time.sleep(2)
                return get_us10y_treasury_yield(_retry_count + 1)
            else:
                raise ValueError(f"Rate limit après {MAX_RETRIES} tentatives. Message: {info_msg}")

        raise ValueError(f"Erreur API: {info_msg}")

    data = response_json.get("data", [])
    if not data:
        raise ValueError(f"Aucune donnée de taux US 10Y retournée. Response: {response_json}")

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = df["value"].astype(float)

    df = df.set_index("date").sort_index()
    df.columns = ["us10y_yield"]
    df.index.name = "time"

    return df


# VIX – stress global du marché
def get_vix_daily(_retry_count: int = 0) -> pd.DataFrame:
    """
    Récupère le VIX en daily
    """
    MAX_RETRIES = 3

    _wait_for_rate_limit()

    params = {
        "function": "TIME_SERIES_DAILY",
        "symbol": "VIX",
        "apikey": API_KEY,
    }

    r = requests.get(BASE_URL, params=params, timeout=30)
    r.raise_for_status()

    response_json = r.json()

    # Vérifier les erreurs API
    if "Information" in response_json:
        info_msg = response_json["Information"]

        if "premium endpoint" in info_msg.lower():
            raise ValueError(f"Endpoint PREMIUM requis. Message: {info_msg}")

        if "rate" in info_msg.lower() or "frequency" in info_msg.lower():
            if _retry_count < MAX_RETRIES:
                print(f"[WARNING] Rate limit. Tentative {_retry_count + 1}/{MAX_RETRIES} dans 2s...")
                time.sleep(2)
                return get_vix_daily(_retry_count + 1)
            else:
                raise ValueError(f"Rate limit après {MAX_RETRIES} tentatives. Message: {info_msg}")

        raise ValueError(f"Erreur API: {info_msg}")

    data = response_json.get("Time Series (Daily)", {})
    if not data:
        raise ValueError(f"Aucune donnée VIX retournée par l'API. Response: {response_json}")

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