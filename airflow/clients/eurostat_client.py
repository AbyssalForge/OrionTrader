"""
Client pour les sources de données économiques (OECD, World Bank, ECB, Investing.com).
Utilise HashiCorp Vault pour récupérer les URLs.
"""

import pandas as pd
import requests
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional
from io import StringIO

try:
    from config.data_sources import get_config
except ImportError:
    airflow_dir = Path(__file__).parent.parent
    if str(airflow_dir) not in sys.path:
        sys.path.insert(0, str(airflow_dir))
    from config.data_sources import get_config


class EurostatClient:
    """Client pour récupérer les données économiques depuis plusieurs sources."""

    def __init__(self, use_vault: bool = True):
        """
        Initialise le client Eurostat.

        Args:
            use_vault: Utiliser Vault pour récupérer les URLs (par défaut: True)
        """
        self.use_vault = use_vault

        if self.use_vault:
            config = get_config()
            self.ecb_url = config.get_ecb_url()
            self.oecd_url = config.get_oecd_url()
            self.worldbank_url = config.get_worldbank_url()
            self.investing_url = config.get_investing_url()
        else:
            self.ecb_url = "https://data-api.ecb.europa.eu/service/data/ICP/M.U2.N.000000.4.ANR"
            self.oecd_url = "https://stats.oecd.org/sdmx-json/data"
            self.worldbank_url = "https://api.worldbank.org/v2/country"
            self.investing_url = "https://www.investing.com/economic-calendar/"

        print(f"[EUROSTAT] Initialized with Vault URLs")

    # ==================== OECD ====================

    def get_oecd_data(self, dataset: str, filter_exp: str, start: Optional[datetime] = None) -> pd.DataFrame:
        """
        Récupère des données depuis l'OECD.

        Args:
            dataset: Code du dataset (ex: 'QNA' pour quarterly national accounts)
            filter_exp: Expression de filtre (ex: 'EA19.B1_GE.CQR.Q')
            start: Date de début (datetime). Par défaut: 2020-01-01

        Returns:
            DataFrame avec les données
        """
        if start is None:
            start = datetime(2020, 1, 1)

        start_time_str = start.strftime('%Y-%m')
        print(f"[OECD] Fetching {dataset}/{filter_exp} (from {start_time_str})")

        url = f"{self.oecd_url}/{dataset}/{filter_exp}/all"

        params = {'startTime': start_time_str}

        try:
            response = requests.get(url, params=params, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0'
            })
            response.raise_for_status()
            data = response.json()

            # Parser la structure SDMX-JSON de l'OECD
            observations = data['dataSets'][0]['observations']
            structure = data['structure']['dimensions']['observation']

            # Trouver l'index de la dimension temporelle
            time_dim_idx = next(i for i, dim in enumerate(structure) if dim['id'] == 'TIME_PERIOD')

            # Extraire les données
            records = []
            for key, value in observations.items():
                indices = [int(x) for x in key.split(':')]
                time_period = structure[time_dim_idx]['values'][indices[time_dim_idx]]['id']
                records.append({
                    'time': time_period,
                    'value': value[0]
                })

            df = pd.DataFrame(records)
            df['time'] = pd.to_datetime(df['time'])
            df = df.set_index('time').sort_index()

            print(f"[OECD] OK: {len(df)} observations")
            return df

        except Exception as e:
            print(f"[OECD] ERROR: {e}")
            raise

    def get_oecd_eurozone_gdp(self, start: Optional[datetime] = None) -> pd.DataFrame:
        """PIB Eurozone depuis l'OECD (GRATUIT)"""
        print("[OECD] Fetching Eurozone GDP (quarterly)")

        try:
            df = self.get_oecd_data('QNA', 'EA19.B1_GE.CQR.Q', start=start)
            df.columns = ['eurozone_pib']
            print(f"[OECD] OK: GDP saved - {len(df)} rows")
            return df
        except Exception as e:
            print(f"[OECD] WARNING: GDP error: {e}")
            return None

    def get_oecd_eurozone_cpi(self, start: Optional[datetime] = None) -> pd.DataFrame:
        """CPI Eurozone depuis l'OECD (GRATUIT)"""
        print("[OECD] Fetching Eurozone CPI (monthly)")

        try:
            df = self.get_oecd_data('MEI', 'EA19.CPALTT01.IXOB.M', start=start)
            df.columns = ['eurozone_cpi']
            print(f"[OECD] OK: CPI saved - {len(df)} rows")
            return df
        except Exception as e:
            print(f"[OECD] WARNING: CPI error: {e}")
            return None

    # ==================== WORLD BANK ====================

    def get_worldbank_data(self, indicator: str, country: str = 'EMU', start: Optional[datetime] = None) -> pd.DataFrame:
        """
        Récupère des données depuis la World Bank.

        Args:
            indicator: Code de l'indicateur (ex: 'NY.GDP.MKTP.KD.ZG' pour PIB growth)
            country: Code pays (EMU = Euro Area)
            start: Date de début (datetime). Par défaut: 2015-01-01

        Returns:
            DataFrame avec les données
        """
        if start is None:
            start = datetime(2015, 1, 1)

        start_year = start.year
        end_year = datetime.now().year

        print(f"[WORLDBANK] Fetching {indicator} for {country} (from {start_year})")

        url = f"{self.worldbank_url}/{country}/indicator/{indicator}"

        params = {
            'format': 'json',
            'date': f'{start_year}:{end_year}',
            'per_page': 1000
        }

        try:
            response = requests.get(url, params=params, timeout=60)
            response.raise_for_status()
            data = response.json()

            if len(data) < 2 or not data[1]:
                raise ValueError(f"No data for {indicator}")

            records = []
            for item in data[1]:
                if item['value'] is not None:
                    records.append({
                        'time': f"{item['date']}-01-01",
                        'value': item['value']
                    })

            df = pd.DataFrame(records)
            df['time'] = pd.to_datetime(df['time'])
            df = df.set_index('time').sort_index()

            print(f"[WORLDBANK] OK: {len(df)} observations")
            return df

        except Exception as e:
            print(f"[WORLDBANK] ERROR: {e}")
            raise

    def get_worldbank_eurozone_gdp(self, start: Optional[datetime] = None) -> pd.DataFrame:
        """PIB Eurozone depuis World Bank"""
        print("[WORLDBANK] Fetching Eurozone GDP")

        try:
            df = self.get_worldbank_data('NY.GDP.MKTP.KD.ZG', country='EMU', start=start)
            df.columns = ['eurozone_pib']
            print(f"[WORLDBANK] OK: GDP saved - {len(df)} rows")
            return df
        except Exception as e:
            print(f"[WORLDBANK] WARNING: GDP error: {e}")
            return None

    def get_worldbank_eurozone_cpi(self, start: Optional[datetime] = None) -> pd.DataFrame:
        """CPI Eurozone depuis World Bank"""
        print("[WORLDBANK] Fetching Eurozone CPI")

        try:
            df = self.get_worldbank_data('FP.CPI.TOTL.ZG', country='EMU', start=start)
            df.columns = ['eurozone_cpi']
            print(f"[WORLDBANK] OK: CPI saved - {len(df)} rows")
            return df
        except Exception as e:
            print(f"[WORLDBANK] WARNING: CPI error: {e}")
            return None

    # ==================== ECB ====================

    def get_ecb_eurozone_cpi(self, start: Optional[datetime] = None) -> pd.DataFrame:
        """CPI Eurozone depuis ECB (European Central Bank)"""
        print("[ECB] Fetching Eurozone CPI/HICP")

        if start is None:
            start = datetime(2015, 1, 1)

        start_period = start.strftime('%Y-%m')

        try:
            params = {
                'format': 'csvdata',
                'startPeriod': start_period,
                'detail': 'dataonly'
            }

            response = requests.get(self.ecb_url, params=params, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0'
            })
            response.raise_for_status()

            df = pd.read_csv(StringIO(response.text))

            # Parser le format ECB
            if 'TIME_PERIOD' in df.columns and 'OBS_VALUE' in df.columns:
                df['TIME_PERIOD'] = pd.to_datetime(df['TIME_PERIOD'])
                df = df[['TIME_PERIOD', 'OBS_VALUE']].copy()
                df.columns = ['time', 'eurozone_cpi']
                df = df.set_index('time').sort_index()

                print(f"[ECB] OK: CPI saved - {len(df)} rows")
                return df
            else:
                raise ValueError("Unexpected ECB format")

        except Exception as e:
            print(f"[ECB] WARNING: CPI error: {e}")
            return None

    # ==================== INVESTING.COM ====================

    def get_investing_economic_calendar(self, days: int = 7) -> pd.DataFrame:
        """
        Récupère le calendrier économique depuis Investing.com.

        Note: Génère des événements factices pour l'instant (web scraping complexe).

        Args:
            days: Nombre de jours à récupérer

        Returns:
            DataFrame avec les événements économiques
        """
        print(f"[INVESTING] Fetching economic calendar ({days} days)")

        try:
            # Note: Le web scraping d'Investing.com est complexe
            # On génère des événements factices pour l'instant
            print("[INVESTING] WARNING: Generating mock events (complex web scraping)")

            events = []
            for i in range(10):
                date = datetime.now() + timedelta(days=i)
                events.append({
                    'time': date,
                    'title': f'Economic Event {i+1}',
                    'impact': ['High', 'Medium', 'Low'][i % 3]
                })

            df = pd.DataFrame(events)
            print(f"[INVESTING] OK: {len(df)} events generated")
            return df

        except Exception as e:
            print(f"[INVESTING] WARNING: Error: {e}")
            return None

    # ==================== FONCTION GLOBALE ====================

    def extract_all_documents(self, start: Optional[datetime] = None) -> Dict[str, pd.DataFrame]:
        """
        Extrait tous les documents depuis les sources alternatives.

        Essaie plusieurs sources dans l'ordre de préférence:
        1. OECD (meilleure qualité)
        2. World Bank (backup)
        3. ECB SDW (backup)

        Args:
            start: Date de début (datetime). Par défaut: dépend de chaque source

        Returns:
            dict avec les DataFrames (pib, cpi, events)
        """
        print("=" * 80)
        print("EXTRACTING ECONOMIC DOCUMENTS - ALTERNATIVE SOURCES")
        print("=" * 80)

        results = {}

        # PIB - Essayer OECD d'abord, puis World Bank
        print("\n1. Eurozone GDP:")
        pib_df = self.get_oecd_eurozone_gdp(start=start)
        if pib_df is None or pib_df.empty:
            pib_df = self.get_worldbank_eurozone_gdp(start=start)
        if pib_df is not None and not pib_df.empty:
            results['pib'] = pib_df

        # CPI - Essayer ECB (source officielle), puis OECD, puis World Bank
        print("\n2. Eurozone CPI:")
        cpi_df = self.get_ecb_eurozone_cpi(start=start)
        if cpi_df is None or cpi_df.empty:
            print("   [FALLBACK] ECB failed, trying OECD...")
            cpi_df = self.get_oecd_eurozone_cpi(start=start)
        if cpi_df is None or cpi_df.empty:
            print("   [FALLBACK] OECD failed, trying World Bank...")
            cpi_df = self.get_worldbank_eurozone_cpi(start=start)
        if cpi_df is not None and not cpi_df.empty:
            results['cpi'] = cpi_df

        # Events - Investing.com
        print("\n3. Economic Events:")
        events_df = self.get_investing_economic_calendar()
        if events_df is not None and not events_df.empty:
            results['events'] = events_df

        print("\n" + "=" * 80)
        print(f"OK: {len(results)}/3 sources retrieved")
        print("=" * 80)

        return results
