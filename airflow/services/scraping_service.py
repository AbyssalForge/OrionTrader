"""
Service de scraping Wikipedia pour les indices boursiers

Scrape les composants des principaux indices:
- CAC 40 (France)
- S&P 500 (USA)
- NASDAQ 100 (USA)
- Dow Jones Industrial Average (USA)
"""

import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, List
from io import StringIO
import time


INDICES_CONFIG = {
    'CAC40': {
        'url': 'https://en.wikipedia.org/wiki/CAC_40',
        'table_index': 3,  # Table avec id="constituents" (40 entreprises)
        'columns_mapping': {
            'Company': 'company_name',
            'Ticker': 'ticker',
            'Sector': 'sector'
        },
        'country_default': 'France',
        'index_name': 'CAC 40'
    },
    'SP500': {
        'url': 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies',
        'table_index': 0,
        'columns_mapping': {
            'Security': 'company_name',
            'Symbol': 'ticker',
            'GICS Sector': 'sector',
            'Headquarters Location': 'country'
        },
        'country_default': 'USA',
        'index_name': 'S&P 500'
    },
    'NASDAQ100': {
        'url': 'https://en.wikipedia.org/wiki/Nasdaq-100',
        'table_index': 3,  # Components table (101 entreprises)
        'columns_mapping': {
            'Company': 'company_name',
            'Ticker': 'ticker',
            'ICB Industry[14]': 'sector'  # Colonne ICB Industry, pas GICS
        },
        'country_default': 'USA',
        'index_name': 'NASDAQ 100'
    },
    'DJIA': {
        'url': 'https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average',
        'table_index': 0,  # Table avec id="constituents" (30 entreprises)
        'columns_mapping': {
            'Company': 'company_name',
            'Symbol': 'ticker',
            'Industry': 'sector'
        },
        'country_default': 'USA',
        'index_name': 'Dow Jones Industrial Average'
    }
}


def scrape_wikipedia_index(index_key: str, config: dict) -> pd.DataFrame:
    """
    Scrape une table Wikipedia pour un indice boursier.

    Args:
        index_key: Clé de l'indice (CAC40, SP500, etc.)
        config: Configuration de scraping pour cet indice

    Returns:
        DataFrame avec les données scrapées
    """
    print(f"[SCRAPING] Scraping {config['index_name']} depuis {config['url']}")

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        response = requests.get(config['url'], headers=headers, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        tables = soup.find_all('table', {'class': 'wikitable'})

        if len(tables) <= config['table_index']:
            raise ValueError(f"Table index {config['table_index']} non trouvée pour {index_key}")

        table = tables[config['table_index']]

        df = pd.read_html(StringIO(str(table)))[0]

        df_renamed = pd.DataFrame()

        for wiki_col, standard_col in config['columns_mapping'].items():
            if wiki_col in df.columns:
                df_renamed[standard_col] = df[wiki_col]
            else:
                print(f"[WARNING] Colonne {wiki_col} non trouvée dans {index_key}")

        if 'country' not in df_renamed.columns:
            df_renamed['country'] = config['country_default']

        df_renamed['index_name'] = config['index_name']
        df_renamed['index_key'] = index_key

        df_renamed['scraped_at'] = datetime.now()

        if 'ticker' in df_renamed.columns:
            df_renamed['ticker'] = df_renamed['ticker'].str.strip()
            df_renamed['ticker'] = df_renamed['ticker'].str.replace(r'\[.*?\]', '', regex=True)
            df_renamed['ticker'] = df_renamed['ticker'].str.split().str[0]  # Garder premier élément

        print(f"[SCRAPING] {config['index_name']}: {len(df_renamed)} entreprises trouvées")

        return df_renamed

    except Exception as e:
        print(f"[SCRAPING] Erreur lors du scraping de {config['index_name']}: {e}")
        return pd.DataFrame()


def scrape_all_indices() -> Dict[str, pd.DataFrame]:
    """
    Scrape tous les indices configurés.

    Returns:
        Dict avec les DataFrames pour chaque indice
    """
    print("[SCRAPING] ==================== DÉBUT SCRAPING WIKIPEDIA ====================")

    results = {}

    for index_key, config in INDICES_CONFIG.items():
        df = scrape_wikipedia_index(index_key, config)

        if not df.empty:
            results[index_key] = df

        time.sleep(1)

    total_companies = sum(len(df) for df in results.values())
    print(f"[SCRAPING] Total: {total_companies} entreprises scrapées depuis {len(results)} indices")
    print("[SCRAPING] ==================== FIN SCRAPING ====================")

    return results


def save_scraped_data_to_parquet(data_dict: Dict[str, pd.DataFrame], output_dir: str) -> Dict[str, str]:
    """
    Sauvegarde les données scrapées en fichiers Parquet.

    Args:
        data_dict: Dict avec les DataFrames pour chaque indice
        output_dir: Répertoire de sortie

    Returns:
        Dict avec les chemins des fichiers Parquet créés
    """
    import os

    os.makedirs(output_dir, exist_ok=True)

    file_paths = {}
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    for index_key, df in data_dict.items():
        if not df.empty:
            filename = f"{index_key.lower()}_{timestamp}.parquet"
            filepath = os.path.join(output_dir, filename)
            df.to_parquet(filepath, index=False)
            file_paths[index_key] = filepath
            print(f"[SCRAPING] Sauvegardé: {filepath} ({len(df)} lignes)")

    return file_paths


def get_ticker_sector_mapping(data_dict: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Crée un mapping ticker → secteur à partir des données scrapées.

    Args:
        data_dict: Dict avec les DataFrames pour chaque indice

    Returns:
        DataFrame avec mapping ticker → secteur
    """
    all_data = pd.concat(data_dict.values(), ignore_index=True)

    mapping = all_data.groupby('ticker').agg({
        'company_name': 'first',
        'sector': 'first',
        'country': 'first',
        'index_name': lambda x: ', '.join(sorted(set(x)))  # Lister tous les indices
    }).reset_index()

    mapping.columns = ['ticker', 'company_name', 'sector', 'country', 'indices']

    return mapping



def get_scraping_stats(data_dict: Dict[str, pd.DataFrame]) -> dict:
    """
    Calcule des statistiques sur les données scrapées.

    Returns:
        Dict avec statistiques
    """
    if not data_dict:
        return {
            'total_indices': 0,
            'total_companies': 0,
            'by_index': {},
            'by_sector': {},
            'by_country': {}
        }

    all_data = pd.concat(data_dict.values(), ignore_index=True)

    stats = {
        'total_indices': len(data_dict),
        'total_companies': len(all_data),
        'unique_tickers': all_data['ticker'].nunique(),
        'by_index': {
            idx: len(df) for idx, df in data_dict.items()
        },
        'by_sector': all_data['sector'].value_counts().to_dict(),
        'by_country': all_data['country'].value_counts().to_dict(),
        'scraped_at': datetime.now().isoformat()
    }

    return stats
