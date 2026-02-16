"""
APIs alternatives GRATUITES pour remplacer Stooq
Aucune clé API requise!

Sources:
1. Yahoo Finance (yfinance) - GRATUIT
2. FRED (Federal Reserve Economic Data) - GRATUIT
3. ECB (European Central Bank) - GRATUIT
4. Investing.com - Web scraping
"""

import pandas as pd
import requests
from datetime import datetime, timedelta
import time

# ============================================================================
# YAHOO FINANCE - Alternative gratuite à Stooq (MEILLEURE!)
# ============================================================================

def get_yahoo_data(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """
    Récupère des données depuis Yahoo Finance (GRATUIT, pas de clé API)

    Args:
        ticker: Symbole Yahoo (ex: 'EURUSD=X', 'DX-Y.NYB', '^VIX', '^GSPC', 'GC=F')
        period: Période ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max')
        interval: Intervalle ('1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo')

    Returns:
        DataFrame avec OHLCV

    Symboles utiles:
        - EURUSD=X : EUR/USD
        - GBPUSD=X : GBP/USD
        - JPY=X : USD/JPY
        - DX-Y.NYB : Dollar Index (DXY)
        - ^VIX : VIX
        - ^GSPC : S&P 500
        - ^DJI : Dow Jones
        - GC=F : Gold Futures
        - SI=F : Silver Futures
    """
    print(f"[YAHOO] Récupération {ticker} (period={period}, interval={interval})")

    # Construire l'URL de l'API Yahoo Finance v8
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"

    params = {
        'period1': 0,  # Epoch 0 pour avoir le max de données
        'period2': int(time.time()),
        'interval': interval,
        'events': 'div,splits',
        'includePrePost': 'false'
    }

    # Mapper period vers timestamps si nécessaire
    if period != 'max':
        end_time = datetime.now()
        if period == '1d':
            start_time = end_time - timedelta(days=1)
        elif period == '5d':
            start_time = end_time - timedelta(days=5)
        elif period == '1mo':
            start_time = end_time - timedelta(days=30)
        elif period == '3mo':
            start_time = end_time - timedelta(days=90)
        elif period == '6mo':
            start_time = end_time - timedelta(days=180)
        elif period == '1y':
            start_time = end_time - timedelta(days=365)
        elif period == '2y':
            start_time = end_time - timedelta(days=730)
        elif period == '5y':
            start_time = end_time - timedelta(days=1825)
        elif period == '10y':
            start_time = end_time - timedelta(days=3650)
        else:
            start_time = end_time - timedelta(days=365)

        params['period1'] = int(start_time.timestamp())

    try:
        response = requests.get(url, params=params, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
        data = response.json()

        # Extraire les données du chart
        chart = data['chart']['result'][0]
        timestamps = chart['timestamp']
        quotes = chart['indicators']['quote'][0]

        # Créer le DataFrame
        df = pd.DataFrame({
            'time': pd.to_datetime(timestamps, unit='s', utc=True),
            'open': quotes['open'],
            'high': quotes['high'],
            'low': quotes['low'],
            'close': quotes['close'],
            'volume': quotes.get('volume', [None] * len(timestamps))
        })

        df = df.set_index('time').sort_index()
        df = df.dropna(subset=['close'])  # Supprimer les lignes sans close

        print(f"[YAHOO] OK: {len(df)} lignes recuperees pour {ticker}")
        return df

    except Exception as e:
        print(f"[YAHOO] ERREUR {ticker}: {e}")
        raise


def get_yahoo_dxy(days: int = 365) -> pd.DataFrame:
    """Dollar Index (DXY) depuis Yahoo Finance"""
    period = f"{days}d" if days < 365 else f"{days//365}y"
    return get_yahoo_data('DX-Y.NYB', period=period, interval='1d')


def get_yahoo_vix(days: int = 365) -> pd.DataFrame:
    """VIX depuis Yahoo Finance"""
    period = f"{days}d" if days < 365 else f"{days//365}y"
    return get_yahoo_data('^VIX', period=period, interval='1d')


def get_yahoo_spx(days: int = 365) -> pd.DataFrame:
    """S&P 500 depuis Yahoo Finance"""
    period = f"{days}d" if days < 365 else f"{days//365}y"
    return get_yahoo_data('^GSPC', period=period, interval='1d')


def get_yahoo_gold(days: int = 365) -> pd.DataFrame:
    """Gold Futures depuis Yahoo Finance"""
    period = f"{days}d" if days < 365 else f"{days//365}y"
    return get_yahoo_data('GC=F', period=period, interval='1d')


def get_yahoo_eurusd(days: int = 365) -> pd.DataFrame:
    """EUR/USD depuis Yahoo Finance"""
    period = f"{days}d" if days < 365 else f"{days//365}y"
    return get_yahoo_data('EURUSD=X', period=period, interval='1d')


# ============================================================================
# FRED (Federal Reserve Economic Data) - Données économiques US
# ============================================================================

def get_fred_data(series_id: str, api_key: str = None) -> pd.DataFrame:
    """
    Récupère des données depuis FRED (Federal Reserve)

    Note: API key optionnelle mais limitée à 120 requêtes/minute sans clé
    Inscrivez-vous sur https://fred.stlouisfed.org/docs/api/api_key.html

    Args:
        series_id: ID de la série FRED (ex: 'DTWEXBGS' pour DXY, 'DGS10' pour US10Y)
        api_key: Clé API FRED (optionnelle)

    Returns:
        DataFrame avec la série temporelle

    Séries utiles:
        - DTWEXBGS : Dollar Index (Trade Weighted)
        - DGS10 : US Treasury 10Y
        - VIXCLS : VIX
        - DEXUSEU : USD/EUR (inverse de EUR/USD)
    """
    print(f"[FRED] Récupération série {series_id}")

    url = f"https://api.stlouisfed.org/fred/series/observations"

    params = {
        'series_id': series_id,
        'file_type': 'json',
        'sort_order': 'asc'
    }

    if api_key:
        params['api_key'] = api_key
    else:
        # Sans clé API, on peut quand même récupérer certaines données
        print("[FRED] ATTENTION: Pas de cle API, limitations possibles")

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        observations = data['observations']
        df = pd.DataFrame(observations)

        df['date'] = pd.to_datetime(df['date'])
        df['value'] = pd.to_numeric(df['value'], errors='coerce')

        df = df[['date', 'value']].set_index('date').sort_index()
        df = df.dropna()
        df.columns = [series_id.lower()]
        df.index.name = 'time'

        print(f"[FRED] OK: {len(df)} observations pour {series_id}")
        return df

    except Exception as e:
        print(f"[FRED] ERREUR {series_id}: {e}")
        raise


# ============================================================================
# ECB (European Central Bank) - Données économiques Eurozone
# ============================================================================

def get_ecb_data(series_key: str, start_date: str = None) -> pd.DataFrame:
    """
    Récupère des données depuis la BCE (Banque Centrale Européenne)

    Args:
        series_key: Clé de la série ECB
        start_date: Date de début (format YYYY-MM-DD)

    Returns:
        DataFrame avec la série temporelle

    Séries utiles:
        - EXR.D.USD.EUR.SP00.A : EUR/USD taux de change
        - FM.B.U2.EUR.4F.KR.MRR_FR.LEV : Taux d'intérêt BCE
    """
    print(f"[ECB] Récupération série {series_key}")

    url = f"https://data-api.ecb.europa.eu/service/data/{series_key}"

    params = {
        'format': 'csvdata',
        'detail': 'dataonly'
    }

    if start_date:
        params['startPeriod'] = start_date

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        from io import StringIO
        df = pd.read_csv(StringIO(response.text))

        # Parser selon le format ECB
        if 'TIME_PERIOD' in df.columns and 'OBS_VALUE' in df.columns:
            df['TIME_PERIOD'] = pd.to_datetime(df['TIME_PERIOD'])
            df = df[['TIME_PERIOD', 'OBS_VALUE']].set_index('TIME_PERIOD')
            df = df.sort_index()
            df.columns = ['value']
            df.index.name = 'time'

        print(f"[ECB] OK: {len(df)} observations pour {series_key}")
        return df

    except Exception as e:
        print(f"[ECB] ERREUR {series_key}: {e}")
        raise


# ============================================================================
# FONCTION GLOBALE - Contexte macro complet avec Yahoo Finance
# ============================================================================

def get_macro_context_yahoo(days: int = 365) -> dict:
    """
    Récupère le contexte macro complet via Yahoo Finance (GRATUIT)

    Avantages vs Stooq:
    - Plus fiable
    - DXY et VIX disponibles
    - Meilleure qualité de données

    Returns:
        dict avec toutes les données macro
    """
    print(f"[YAHOO] Récupération contexte macro complet ({days} jours)...")

    context = {}
    assets = [
        ('eurusd', 'EUR/USD', lambda d: get_yahoo_data('EURUSD=X', period=f'{d}d' if d<365 else '1y')),
        ('gbpusd', 'GBP/USD', lambda d: get_yahoo_data('GBPUSD=X', period=f'{d}d' if d<365 else '1y')),
        ('usdjpy', 'USD/JPY', lambda d: get_yahoo_data('JPY=X', period=f'{d}d' if d<365 else '1y')),
        ('dxy', 'Dollar Index (DXY)', get_yahoo_dxy),
        ('spx', 'S&P 500', get_yahoo_spx),
        ('vix', 'VIX', get_yahoo_vix),
        ('dji', 'Dow Jones', lambda d: get_yahoo_data('^DJI', period=f'{d}d' if d<365 else '1y')),
        ('gold', 'Gold', get_yahoo_gold),
        ('silver', 'Silver', lambda d: get_yahoo_data('SI=F', period=f'{d}d' if d<365 else '1y')),
    ]

    success_count = 0
    failed_assets = []

    for i, (key, name, func) in enumerate(assets, 1):
        try:
            print(f"[YAHOO] {i}/{len(assets)} - {name}...")
            context[key] = func(days)
            success_count += 1
            time.sleep(0.5)  # Petit délai pour éviter rate limiting
        except Exception as e:
            print(f"[YAHOO] {name} non disponible: {str(e)}")
            failed_assets.append(name)

    print(f"[YAHOO] OK: {success_count}/{len(assets)} actifs recuperes")

    if failed_assets:
        print(f"[YAHOO] ATTENTION: Actifs echoues: {', '.join(failed_assets)}")

    if success_count == 0:
        raise ValueError("Aucun actif n'a pu être récupéré depuis Yahoo Finance")

    return context


# ============================================================================
# EXEMPLE D'UTILISATION
# ============================================================================

if __name__ == "__main__":
    print("="*80)
    print("TEST DES APIS ALTERNATIVES GRATUITES")
    print("="*80)

    # Test Yahoo Finance
    print("\n1. Test Yahoo Finance:")
    try:
        df_dxy = get_yahoo_dxy(days=30)
        print(f"   DXY: {len(df_dxy)} lignes")
        print(f"   Période: {df_dxy.index.min()} -> {df_dxy.index.max()}")
    except Exception as e:
        print(f"   Erreur DXY: {e}")

    try:
        df_vix = get_yahoo_vix(days=30)
        print(f"   VIX: {len(df_vix)} lignes")
        print(f"   Période: {df_vix.index.min()} -> {df_vix.index.max()}")
    except Exception as e:
        print(f"   Erreur VIX: {e}")

    # Test contexte complet
    print("\n2. Test contexte macro complet:")
    try:
        context = get_macro_context_yahoo(days=30)
        print(f" {len(context)} actifs récupérés")
        for key, df in context.items():
            print(f"   - {key}: {len(df)} lignes")
    except Exception as e:
        print(f"   Erreur: {e}")

    print("\n" + "="*80)


# ============================================================================
# PROXIES MACRO QUOTIDIENS - Source 3 (Alternative PIB/CPI)
# ============================================================================

def get_macro_proxies_daily(days: int = 730) -> dict:
    """
    SOURCE 3: Proxies macro quotidiens (alternative aux données économiques mensuelles)

    Remplace PIB/CPI par des indicateurs quotidiens qui capturent la même information:
    - Treasury yields (10Y, 5Y): Proxy inflation et anticipation récession
    - VSTOXX: Proxy stress macro Europe

    Avantages vs PIB/CPI:
    - Fréquence quotidienne (vs mensuel/annuel)
    - Pas de gaps temporels
    - Meilleure corrélation avec trading M15
    - Données toujours disponibles

    Args:
        days: Nombre de jours à récupérer (défaut 730 = 2 ans)

    Returns:
        dict avec DataFrames pour chaque proxy
    """
    print(f"[PROXIES MACRO] Récupération proxies quotidiens ({days} jours)")

    proxies = {}
    period_str = f'{days}d' if days < 365 else ('2y' if days < 1825 else '5y')

    # 1. US Treasury 10 ans (proxy inflation)
    # Quand inflation attendue ↑ → Taux 10Y ↑
    try:
        print("[PROXIES] Treasury 10Y (^TNX) - proxy inflation...")
        tnx = get_yahoo_data('^TNX', period=period_str)
        if not tnx.empty:
            proxies['treasury_10y'] = tnx[['close']].rename(columns={'close': 'treasury_10y_yield'})
            print(f"[PROXIES] OK: Treasury 10Y - {len(tnx)} lignes")
        else:
            print("[PROXIES] ATTENTION: Treasury 10Y vide")
    except Exception as e:
        print(f"[PROXIES] ERREUR Treasury 10Y: {e}")

    # 2. US Treasury 5 ans (proxy anticipation moyen terme)
    try:
        print("[PROXIES] Treasury 5Y (^FVX) - proxy anticipation...")
        fvx = get_yahoo_data('^FVX', period=period_str)
        if not fvx.empty:
            proxies['treasury_5y'] = fvx[['close']].rename(columns={'close': 'treasury_5y_yield'})
            print(f"[PROXIES] OK: Treasury 5Y - {len(fvx)} lignes")
        else:
            print("[PROXIES] ATTENTION: Treasury 5Y vide")
    except Exception as e:
        print(f"[PROXIES] ERREUR Treasury 5Y: {e}")

    # 3. VSTOXX (volatilité Eurostoxx 50 - proxy stress macro Europe)
    # Alternative: Si VSTOXX échoue, utiliser VDAX (volatilité DAX allemand)
    try:
        print("[PROXIES] VSTOXX (^V2TX) - proxy stress Europe...")
        vstoxx = get_yahoo_data('^V2TX', period=period_str)
        if not vstoxx.empty:
            proxies['vstoxx'] = vstoxx[['close']].rename(columns={'close': 'vstoxx_close'})
            print(f"[PROXIES] OK: VSTOXX - {len(vstoxx)} lignes")
        else:
            print("[PROXIES] ATTENTION: VSTOXX vide, tentative VDAX...")
            # Fallback sur VDAX
            vdax = get_yahoo_data('^VDAX', period=period_str)
            if not vdax.empty:
                proxies['vstoxx'] = vdax[['close']].rename(columns={'close': 'vstoxx_close'})
                print(f"[PROXIES] OK: VDAX (fallback) - {len(vdax)} lignes")
    except Exception as e:
        print(f"[PROXIES] ERREUR VSTOXX/VDAX: {e}")

    print(f"[PROXIES MACRO] OK: {len(proxies)}/3 proxies récupérés")
    return proxies


def save_macro_proxies_to_parquet(proxies: dict, base_path: str = "data/proxies") -> dict:
    """
    Sauvegarde les proxies macro en fichiers parquet

    Args:
        proxies: dict retourné par get_macro_proxies_daily()
        base_path: chemin de base pour sauvegarder les parquets

    Returns:
        dict avec les chemins des fichiers créés
    """
    import os
    os.makedirs(base_path, exist_ok=True)

    paths = {}

    for key, df in proxies.items():
        if df is not None and not df.empty:
            file_path = os.path.join(base_path, f"{key}.parquet")

            # S'assurer que l'index est 'time'
            if df.index.name != 'time':
                df = df.reset_index()
                if 'index' in df.columns:
                    df = df.rename(columns={'index': 'time'})
                df = df.set_index('time')

            df.to_parquet(file_path)
            paths[key] = file_path
            print(f"[PROXIES] Sauvegarde: {file_path}")

    return paths
