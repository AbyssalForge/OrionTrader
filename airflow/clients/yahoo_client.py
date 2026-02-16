"""
Client Yahoo Finance pour récupérer les données de marché.
Utilise HashiCorp Vault pour récupérer l'URL de base.
"""

import pandas as pd
import requests
import time
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional

try:
    from config.data_sources import get_config
except ImportError:
    airflow_dir = Path(__file__).parent.parent
    if str(airflow_dir) not in sys.path:
        sys.path.insert(0, str(airflow_dir))
    from config.data_sources import get_config


class YahooFinanceClient:
    """Client pour interagir avec Yahoo Finance API."""

    def __init__(self, use_vault: bool = True):
        """
        Initialise le client Yahoo Finance.

        Args:
            use_vault: Utiliser Vault pour récupérer l'URL (par défaut: True)
        """
        self.use_vault = use_vault

        if self.use_vault:
            config = get_config()
            self.base_url = config.get_yahoo_base_url()
        else:
            self.base_url = "https://query1.finance.yahoo.com/v8/finance/chart"

        print(f"[YAHOO] Initialized with base URL: {self.base_url}")

    def get_data(self, ticker: str, start: Optional[datetime] = None, end: Optional[datetime] = None, interval: str = "1d") -> pd.DataFrame:
        """
        Récupère des données depuis Yahoo Finance.

        Args:
            ticker: Symbole Yahoo (ex: 'EURUSD=X', 'DX-Y.NYB', '^VIX', '^GSPC', 'GC=F')
            start: Date de début (datetime). Par défaut: 1 an avant end
            end: Date de fin (datetime). Par défaut: maintenant
            interval: Intervalle ('1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo')
                     Par défaut: '1d' (daily - contexte macro)

        Returns:
            DataFrame avec OHLCV
        """
        # Date de fin par défaut = maintenant
        if end is None:
            end_time = datetime.now()
        else:
            end_time = end

        # Date de début par défaut = 1 an avant end
        if start is None:
            start_time = end_time - timedelta(days=365)
        else:
            start_time = start

        print(f"[YAHOO] Fetching {ticker} (start={start_time.date()}, end={end_time.date()}, interval={interval})")

        url = f"{self.base_url}/{ticker}"

        params = {
            'period1': int(start_time.timestamp()),
            'period2': int(end_time.timestamp()),
            'interval': interval,
            'events': 'div,splits',
            'includePrePost': 'false'
        }

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
            df = df.dropna(subset=['close'])

            if len(df) > 0:
                actual_start = df.index.min().date()
                actual_end = df.index.max().date()
                print(f"[YAHOO] OK: {ticker} - {len(df)} rows (from {actual_start} to {actual_end})")
            else:
                print(f"[YAHOO] WARNING: {ticker} - No data returned")

            return df

        except Exception as e:
            print(f"[YAHOO] ERROR {ticker}: {e}")
            raise

    def get_macro_context(self, start: Optional[datetime] = None, end: Optional[datetime] = None, interval: str = "1d") -> Dict[str, pd.DataFrame]:
        """
        Récupère le contexte macro complet via Yahoo Finance.

        Args:
            start: Date de début (datetime). Par défaut: 1 an avant end
            end: Date de fin (datetime). Par défaut: maintenant
            interval: Intervalle ('1d', '1h', '15m', etc.). Par défaut: '1d' (daily - contexte macro)

        Returns:
            dict avec toutes les données macro
        """
        if end is None:
            end = datetime.now()

        if start is None:
            start = end - timedelta(days=365)

        print(f"[YAHOO] Fetching macro context (from {start.date()} to {end.date()}, interval={interval})...")

        context = {}

        assets = [
            ('eurusd', 'EUR/USD', 'EURUSD=X'),
            ('gbpusd', 'GBP/USD', 'GBPUSD=X'),
            ('usdjpy', 'USD/JPY', 'JPY=X'),
            ('dxy', 'Dollar Index (DXY)', 'DX-Y.NYB'),
            ('spx', 'S&P 500', '^GSPC'),
            ('vix', 'VIX', '^VIX'),
            ('dji', 'Dow Jones', '^DJI'),
            ('gold', 'Gold', 'GC=F'),
            ('silver', 'Silver', 'SI=F'),
        ]

        success_count = 0
        failed_assets = []

        for i, (key, name, ticker) in enumerate(assets, 1):
            try:
                print(f"[YAHOO] {i}/{len(assets)} - {name}...")
                context[key] = self.get_data(ticker, start=start, end=end, interval=interval)
                success_count += 1
                time.sleep(0.5)  # Rate limiting
            except Exception as e:
                print(f"[YAHOO] {name} unavailable: {str(e)}")
                failed_assets.append(name)

        print(f"[YAHOO] OK: {success_count}/{len(assets)} assets fetched")

        if failed_assets:
            print(f"[YAHOO] WARNING: Failed assets: {', '.join(failed_assets)}")

        if success_count == 0:
            raise ValueError("No assets could be fetched from Yahoo Finance")

        return context

    def get_dxy(self, start: Optional[datetime] = None) -> pd.DataFrame:
        """Dollar Index (DXY)"""
        return self.get_data('DX-Y.NYB', start=start, interval='1d')

    def get_vix(self, start: Optional[datetime] = None) -> pd.DataFrame:
        """VIX"""
        return self.get_data('^VIX', start=start, interval='1d')

    def get_spx(self, start: Optional[datetime] = None) -> pd.DataFrame:
        """S&P 500"""
        return self.get_data('^GSPC', start=start, interval='1d')

    def get_gold(self, start: Optional[datetime] = None) -> pd.DataFrame:
        """Gold Futures"""
        return self.get_data('GC=F', start=start, interval='1d')

    def get_eurusd(self, start: Optional[datetime] = None) -> pd.DataFrame:
        """EUR/USD"""
        return self.get_data('EURUSD=X', start=start, interval='1d')
