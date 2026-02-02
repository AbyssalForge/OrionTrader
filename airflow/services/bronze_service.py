"""
Bronze Layer Service - Extraction des données brutes
Les données sont sauvegardées en fichiers .parquet

Utilise les clients modulaires pour interagir avec les sources de données:
- MT5Client pour MetaTrader5
- YahooFinanceClient pour Yahoo Finance
- EurostatClient pour les sources économiques
"""

import os
import pandas as pd

from clients.yahoo_client import YahooFinanceClient
from clients.eurostat_client import EurostatClient
from services.scraping_service import scrape_all_indices, save_scraped_data_to_parquet, get_scraping_stats


def extract_yahoo_data(start=None, end=None, include_intraday=True):
    """
    Extrait TOUTES les données Yahoo Finance et les sauvegarde en .parquet

    Données extraites:
    - EUR/USD 15m (intraday - remplace MT5)
    - Actifs macro daily: EUR/USD, GBP/USD, USD/JPY, DXY, S&P500, VIX, DJI, Or, Argent

    Args:
        start: Date de début (datetime). Par défaut: 1 an avant end
        end: Date de fin (datetime). Par défaut: maintenant
        include_intraday: Si True, inclut EUR/USD 15m (par défaut: True)

    Returns:
        dict: Dictionnaire {symbole: chemin_fichier}
              Clés: 'eurusd_15m', 'eurusd', 'gbpusd', 'usdjpy', 'dxy', 'spx', 'vix', 'dji', 'gold', 'silver'
    """
    paths = {}

    print("=" * 70)
    print("[BRONZE/YAHOO] Extraction Yahoo Finance - TOUTES SOURCES")
    print("=" * 70)

    # Utiliser le client Yahoo Finance (avec Vault)
    yahoo_client = YahooFinanceClient(use_vault=True)

    # ========================================================================
    # 1. EXTRACTION INTRADAY: EUR/USD 15 minutes (remplace MT5)
    # ========================================================================
    if include_intraday and start and end:
        print(f"\n[BRONZE/YAHOO] 1️⃣ Extraction EUR/USD 15m (intraday): {start.date()} -> {end.date()}")

        base_path_intraday = "data/forex_intraday"
        os.makedirs(base_path_intraday, exist_ok=True)

        try:
            df_15m = yahoo_client.get_data(
                ticker='EURUSD=X',
                start=start,
                end=end,
                interval='15m'
            )

            if len(df_15m) > 0:
                path_15m = f"{base_path_intraday}/eurusd_15m.parquet"
                df_15m.to_parquet(path_15m)
                paths['eurusd_15m'] = path_15m
                print(f"[BRONZE/YAHOO] ✅ EUR/USD 15m: {len(df_15m)} lignes sauvegardées")
            else:
                # Créer un DataFrame vide avec la structure attendue
                print(f"[BRONZE/YAHOO] ⚠️  EUR/USD 15m: Aucune donnée (Yahoo limite intraday à ~7 jours)")
                print(f"[BRONZE/YAHOO] ℹ️  Création fichier vide pour compatibilité pipeline")
                empty_df = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
                empty_df.index.name = 'time'
                path_15m = f"{base_path_intraday}/eurusd_15m_empty.parquet"
                empty_df.to_parquet(path_15m)
                paths['eurusd_15m'] = path_15m
        except Exception as e:
            print(f"[BRONZE/YAHOO] ❌ Erreur EUR/USD 15m: {e}")
            # Créer quand même un fichier vide pour ne pas bloquer le pipeline
            print(f"[BRONZE/YAHOO] ℹ️  Création fichier vide suite à l'erreur")
            empty_df = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
            empty_df.index.name = 'time'
            path_15m = f"{base_path_intraday}/eurusd_15m_empty.parquet"
            empty_df.to_parquet(path_15m)
            paths['eurusd_15m'] = path_15m

    # ========================================================================
    # 2. EXTRACTION DAILY: Actifs macro (indices, forex, commodités)
    # ========================================================================
    print(f"\n[BRONZE/YAHOO] 2️⃣ Extraction actifs macro (daily)")

    base_path = "data/api"
    os.makedirs(base_path, exist_ok=True)

    macro_context = yahoo_client.get_macro_context(start=start, end=end)
    print(f"[BRONZE/YAHOO] OK: {len(macro_context)} actifs macro extraits")
    asset_mapping = {
        'eurusd': 'EUR/USD',
        'gbpusd': 'GBP/USD',
        'usdjpy': 'USD/JPY',
        'dxy': 'DXY (Dollar Index)',
        'spx': 'S&P 500',
        'vix': 'VIX',
        'dji': 'Dow Jones',
        'gold': 'Or (Gold)',
        'silver': 'Argent (Silver)'
    }

    total_rows = 0
    for key, name in asset_mapping.items():
        if key in macro_context:
            df = macro_context[key]
            num_rows = len(df)
            total_rows += num_rows

            # Afficher les dates min/max pour debug
            date_min = df.index.min()
            date_max = df.index.max()
            print(f"[BRONZE/YAHOO] {name}: {num_rows} lignes (de {date_min.date()} à {date_max.date()})")

            file_path = f"{base_path}/{key}_daily.parquet"
            df.to_parquet(file_path)
            paths[key] = file_path
        else:
            print(f"[BRONZE/YAHOO] ATTENTION: {name} non disponible, ignore")

    print(f"[BRONZE/YAHOO] Total lignes actifs daily: {total_rows}")

    # ========================================================================
    # 3. RÉSUMÉ FINAL
    # ========================================================================
    print("\n" + "=" * 70)
    print(f"[BRONZE/YAHOO] ✅ EXTRACTION TERMINÉE")
    print(f"   Total fichiers: {len(paths)}")
    if 'eurusd_15m' in paths:
        print(f"   - Intraday: EUR/USD 15m ✅")
    print(f"   - Daily: {len(paths) - (1 if 'eurusd_15m' in paths else 0)} actifs macro ✅")
    print("=" * 70)

    return paths


def extract_eurostat_data(start=None):
    """
    Extrait les données économiques et les sauvegarde en .parquet

    MODIFIÉ: Utilise EurostatClient avec Vault
    Sources: OECD + World Bank + ECB + Investing.com
    Avantages: PIB et CPI à jour, pas de problème de période temporelle

    Args:
        start: Date de début (datetime). Par défaut: varie selon la source (2015-2020)

    Returns:
        dict: Dictionnaire {type: chemin_fichier} (pib, cpi, events)
    """
    base_path = "data/documents"
    os.makedirs(base_path, exist_ok=True)

    print("[BRONZE/DOCUMENTS] Extraction documents economiques via Client...")

    # Utiliser le client Eurostat (avec Vault)
    eurostat_client = EurostatClient(use_vault=True)
    documents = eurostat_client.extract_all_documents(start=start)

    # Sauvegarder les DataFrames en parquet
    paths = {}
    for key, df in documents.items():
        if df is not None and not df.empty:
            file_path = f"{base_path}/{key}.parquet"
            df.to_parquet(file_path)
            paths[key] = file_path
            print(f"[BRONZE/DOCUMENTS] Sauvegarde {key}: {file_path}")

    print(f"[BRONZE/DOCUMENTS] OK: {len(paths)} documents sauvegardes")
    print(f"[BRONZE/DOCUMENTS]   - PIB: {paths.get('pib')}")
    print(f"[BRONZE/DOCUMENTS]   - CPI: {paths.get('cpi')}")
    print(f"[BRONZE/DOCUMENTS]   - Events: {paths.get('events')}")

    return paths


def extract_wikipedia_indices():
    """
    Scrape les indices boursiers depuis Wikipedia et sauvegarde en .parquet

    Sources:
    - CAC 40 (France)
    - S&P 500 (USA)
    - NASDAQ 100 (USA)
    - Dow Jones Industrial Average (USA)

    Returns:
        dict: Dictionnaire {index_key: chemin_fichier}
    """
    base_path = "data/wikipedia"
    os.makedirs(base_path, exist_ok=True)

    print("[BRONZE/WIKIPEDIA] ==================== DÉBUT SCRAPING ====================")

    # Scraper tous les indices
    indices_data = scrape_all_indices()

    if not indices_data:
        print("[BRONZE/WIKIPEDIA] ❌ Aucune donnée scrapée")
        return {}

    # Sauvegarder en parquet
    file_paths = save_scraped_data_to_parquet(indices_data, base_path)

    # Afficher statistiques
    stats = get_scraping_stats(indices_data)
    print(f"[BRONZE/WIKIPEDIA] ✅ Statistiques:")
    print(f"[BRONZE/WIKIPEDIA]   - Indices: {stats['total_indices']}")
    print(f"[BRONZE/WIKIPEDIA]   - Entreprises: {stats['total_companies']}")
    print(f"[BRONZE/WIKIPEDIA]   - Tickers uniques: {stats['unique_tickers']}")

    print(f"[BRONZE/WIKIPEDIA] Répartition par indice:")
    for idx, count in stats['by_index'].items():
        print(f"[BRONZE/WIKIPEDIA]   - {idx}: {count} entreprises")

    print(f"[BRONZE/WIKIPEDIA] Top 5 secteurs:")
    for sector, count in list(stats['by_sector'].items())[:5]:
        print(f"[BRONZE/WIKIPEDIA]   - {sector}: {count} entreprises")

    print(f"[BRONZE/WIKIPEDIA] ==================== FIN SCRAPING ====================")

    return file_paths
