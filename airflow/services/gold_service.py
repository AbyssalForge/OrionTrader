"""
Gold Layer Service v3.0 - Load vers 4 tables séparées
Charge les .parquet transformés (Silver) dans les 4 tables
"""

from datetime import datetime
import pandas as pd

from utils.db_helper import get_db_session
from models import MT5EURUSDM15, YahooFinanceDaily, DocumentsMacro, MarketSnapshotM15, WikipediaIndices


# ============================================================================
# LOAD 1/4 - MT5
# ============================================================================

def load_mt5_to_db(mt5_parquet: str, pipeline_run_id: str = None):
    """
    Charge les features MT5 vers la table mt5_eurusd_m15

    Args:
        mt5_parquet: Chemin du fichier .parquet MT5
        pipeline_run_id: ID du run pipeline

    Returns:
        dict: Résultat avec status, rows
    """
    print(f"[GOLD/MT5] Chargement MT5 depuis {mt5_parquet}...")

    df = pd.read_parquet(mt5_parquet)

    if df.index.name == 'time':
        df = df.reset_index()

    df['time'] = pd.to_datetime(df['time'], utc=True)

    session = get_db_session()
    if not pipeline_run_id:
        pipeline_run_id = datetime.now().isoformat()

    try:
        inserted = 0
        for _, row in df.iterrows():
            record = MT5EURUSDM15(
                time=row['time'],
                open=row.get('open'),
                high=row.get('high'),
                low=row.get('low'),
                close=row.get('close'),
                tick_volume=row.get('tick_volume'),
                close_diff=row.get('close_diff'),
                close_return=row.get('close_return'),
                high_low_range=row.get('high_low_range'),
                volatility_1h=row.get('volatility_1h'),
                volatility_4h=row.get('volatility_4h'),
                momentum_15m=row.get('momentum_15m'),
                momentum_1h=row.get('momentum_1h'),
                momentum_4h=row.get('momentum_4h'),
                body=row.get('body'),
                upper_shadow=row.get('upper_shadow'),
                lower_shadow=row.get('lower_shadow'),
                pipeline_run_id=pipeline_run_id
            )
            session.merge(record)
            inserted += 1

            if inserted % 5000 == 0:
                session.commit()
                print(f"[GOLD/MT5]   {inserted} lignes...")

        session.commit()
        print(f"[GOLD/MT5] OK: {inserted} lignes chargées")

        return {
            'status': 'success',
            'table': 'mt5_eurusd_m15',
            'rows': inserted,
            'pipeline_run_id': pipeline_run_id
        }

    except Exception as e:
        session.rollback()
        print(f"[GOLD/MT5] ERREUR: {e}")
        raise
    finally:
        session.close()


# ============================================================================
# LOAD 2/4 - YAHOO FINANCE
# ============================================================================

def load_yahoo_to_db(yahoo_parquet: str, pipeline_run_id: str = None):
    """
    Charge les features Yahoo vers la table yahoo_finance_daily

    Args:
        yahoo_parquet: Chemin du fichier .parquet Yahoo
        pipeline_run_id: ID du run pipeline

    Returns:
        dict: Résultat avec status, rows
    """
    print(f"[GOLD/YAHOO] Chargement Yahoo depuis {yahoo_parquet}...")

    df = pd.read_parquet(yahoo_parquet)

    if df.index.name == 'time':
        df = df.reset_index()

    df['time'] = pd.to_datetime(df['time'], utc=True)

    session = get_db_session()
    if not pipeline_run_id:
        pipeline_run_id = datetime.now().isoformat()

    try:
        inserted = 0
        for _, row in df.iterrows():
            record = YahooFinanceDaily(
                time=row['time'],
                spx_close=row.get('spx_close'),
                spx_trend=row.get('spx_trend'),
                risk_on=row.get('risk_on'),
                gold_close=row.get('gold_close'),
                gold_trend=row.get('gold_trend'),
                safe_haven=row.get('safe_haven'),
                dxy_close=row.get('dxy_close'),
                dxy_trend_1h=row.get('dxy_trend_1h'),
                dxy_trend_4h=row.get('dxy_trend_4h'),
                dxy_strength=row.get('dxy_strength'),
                vix_close=row.get('vix_close'),
                vix_level=row.get('vix_level'),
                vix_change=row.get('vix_change'),
                market_stress=row.get('market_stress'),
                pipeline_run_id=pipeline_run_id
            )
            session.merge(record)
            inserted += 1

        session.commit()
        print(f"[GOLD/YAHOO] OK: {inserted} lignes chargées")

        return {
            'status': 'success',
            'table': 'yahoo_finance_daily',
            'rows': inserted,
            'pipeline_run_id': pipeline_run_id
        }

    except Exception as e:
        session.rollback()
        print(f"[GOLD/YAHOO] ERREUR: {e}")
        raise
    finally:
        session.close()


# ============================================================================
# LOAD 3/4 - DOCUMENTS MACRO
# ============================================================================

def load_documents_to_db(documents_parquet: str, pipeline_run_id: str = None):
    """
    Charge les documents macro vers la table documents_macro

    Args:
        documents_parquet: Chemin du fichier .parquet Documents
        pipeline_run_id: ID du run pipeline

    Returns:
        dict: Résultat avec status, rows
    """
    print(f"[GOLD/DOCS] Chargement Documents depuis {documents_parquet}...")

    df = pd.read_parquet(documents_parquet)

    if df.index.name == 'time':
        df = df.reset_index()

    df['time'] = pd.to_datetime(df['time'], utc=True)

    session = get_db_session()
    if not pipeline_run_id:
        pipeline_run_id = datetime.now().isoformat()

    try:
        inserted = 0
        for _, row in df.iterrows():
            # Conversion NaN -> None pour colonnes Float et Integer
            def safe_get(key, default=None):
                val = row.get(key, default)
                if pd.isna(val):
                    return default
                return val

            # Conversion spéciale pour Integer (NaN -> 0 ou None)
            inflation_pressure = row.get('inflation_pressure')
            if pd.isna(inflation_pressure):
                inflation_pressure = None
            else:
                inflation_pressure = int(inflation_pressure)

            record = DocumentsMacro(
                time=row['time'],
                data_type=safe_get('data_type'),
                frequency=safe_get('frequency'),
                eurozone_pib=safe_get('eurozone_pib'),
                pib_change=safe_get('pib_change'),
                pib_growth=safe_get('pib_growth'),
                eurozone_cpi=safe_get('eurozone_cpi'),
                cpi_change=safe_get('cpi_change'),
                inflation_pressure=inflation_pressure,
                event_title=safe_get('event_title'),
                event_impact=safe_get('event_impact'),
                event_impact_score=safe_get('event_impact_score'),
                pipeline_run_id=pipeline_run_id
            )
            session.merge(record)
            inserted += 1

        session.commit()
        print(f"[GOLD/DOCS] OK: {inserted} lignes chargées")

        return {
            'status': 'success',
            'table': 'documents_macro',
            'rows': inserted,
            'pipeline_run_id': pipeline_run_id
        }

    except Exception as e:
        session.rollback()
        print(f"[GOLD/DOCS] ERREUR: {e}")
        raise
    finally:
        session.close()


# ============================================================================
# LOAD 4/4 - MARKET SNAPSHOT
# ============================================================================

def load_market_snapshot_to_db(snapshot_parquet: str, pipeline_run_id: str = None):
    """
    Charge le market snapshot vers la table market_snapshot_m15

    Args:
        snapshot_parquet: Chemin du fichier .parquet Market Snapshot
        pipeline_run_id: ID du run pipeline

    Returns:
        dict: Résultat avec status, rows
    """
    print(f"[GOLD/SNAPSHOT] Chargement Market Snapshot depuis {snapshot_parquet}...")

    df = pd.read_parquet(snapshot_parquet)

    if df.index.name == 'time':
        df = df.reset_index()

    df['time'] = pd.to_datetime(df['time'], utc=True)
    df['mt5_time'] = pd.to_datetime(df['mt5_time'], utc=True)
    df['yahoo_time'] = pd.to_datetime(df['yahoo_time'], utc=True)
    df['docs_time'] = pd.to_datetime(df['docs_time'], utc=True)

    session = get_db_session()
    if not pipeline_run_id:
        pipeline_run_id = datetime.now().isoformat()

    try:
        inserted = 0
        for _, row in df.iterrows():
            # Conversion NaN -> None pour colonnes optionnelles
            def safe_get(key, default=None):
                val = row.get(key, default)
                if pd.isna(val):
                    return default
                return val

            record = MarketSnapshotM15(
                time=row['time'],
                mt5_time=row['mt5_time'],
                yahoo_time=safe_get('yahoo_time'),
                docs_time=safe_get('docs_time'),
                # Features composites
                macro_micro_aligned=safe_get('macro_micro_aligned', 0),
                euro_strength_bias=safe_get('euro_strength_bias', 0),
                # Régimes
                regime_composite=safe_get('regime_composite', 'neutral'),
                volatility_regime=safe_get('volatility_regime', 'normal'),
                # Scores
                signal_confidence_score=safe_get('signal_confidence_score', 0.0),
                signal_divergence_count=safe_get('signal_divergence_count', 0),
                trend_strength_composite=safe_get('trend_strength_composite', 0.0),
                # Event
                event_window_active=safe_get('event_window_active', False),
                # Metadata
                pipeline_run_id=pipeline_run_id
            )
            session.merge(record)
            inserted += 1

            if inserted % 5000 == 0:
                session.commit()
                print(f"[GOLD/SNAPSHOT]   {inserted} lignes...")

        session.commit()
        print(f"[GOLD/SNAPSHOT] OK: {inserted} lignes chargées")

        return {
            'status': 'success',
            'table': 'market_snapshot_m15',
            'rows': inserted,
            'pipeline_run_id': pipeline_run_id
        }

    except Exception as e:
        session.rollback()
        print(f"[GOLD/SNAPSHOT] ERREUR: {e}")
        raise
    finally:
        session.close()
        
def load_wikipedia_to_db(wikipedia_parquet: str, pipeline_run_id: str = None):
    """
    Charge les données Wikipedia vers la table wikipedia_indices

    Args:
        wikipedia_parquet: Chemin du fichier .parquet Wikipedia
        pipeline_run_id: ID du run pipeline

    Returns:
        dict: Résultat avec status, rows
    """
    print(f"[GOLD/WIKIPEDIA] Chargement Wikipedia depuis {wikipedia_parquet}...")

    if not wikipedia_parquet:
        print("[GOLD/WIKIPEDIA] ❌ Aucun fichier fourni")
        return {
            'status': 'error',
            'table': 'wikipedia_indices',
            'rows': 0,
            'message': 'No parquet file provided'
        }

    df = pd.read_parquet(wikipedia_parquet)

    session = get_db_session()
    if not pipeline_run_id:
        pipeline_run_id = datetime.now().isoformat()

    try:
        inserted = 0

        for _, row in df.iterrows():
            record = WikipediaIndices(
                ticker=row.get('ticker'),
                company_name=row.get('company_name'),
                sector=row.get('sector'),
                country=row.get('country'),
                region=row.get('region'),
                index_name=row.get('index_name'),
                index_key=row.get('index_key'),
                num_indices=row.get('num_indices'),
                is_multi_index=row.get('is_multi_index', False),
                ticker_company=row.get('ticker_company'),
                scraped_at=pd.to_datetime(row.get('scraped_at')) if row.get('scraped_at') else None,
                transformed_at=pd.to_datetime(row.get('transformed_at')) if row.get('transformed_at') else None,
                pipeline_run_id=pipeline_run_id
            )
            session.merge(record)  # Merge pour gérer les duplicates (upsert)
            inserted += 1

            if inserted % 100 == 0:
                session.commit()
                print(f"[GOLD/WIKIPEDIA]   {inserted} tickers...")

        session.commit()
        print(f"[GOLD/WIKIPEDIA] OK: {inserted} tickers chargés")

        # Statistiques
        total_sectors = df['sector'].nunique() if 'sector' in df.columns else 0
        total_countries = df['country'].nunique() if 'country' in df.columns else 0

        print(f"[GOLD/WIKIPEDIA] Statistiques:")
        print(f"[GOLD/WIKIPEDIA]   - Secteurs uniques: {total_sectors}")
        print(f"[GOLD/WIKIPEDIA]   - Pays uniques: {total_countries}")

        return {
            'status': 'success',
            'table': 'wikipedia_indices',
            'rows': inserted,
            'sectors': total_sectors,
            'countries': total_countries,
            'pipeline_run_id': pipeline_run_id
        }

    except Exception as e:
        session.rollback()
        print(f"[GOLD/WIKIPEDIA] ERREUR: {e}")
        raise
    finally:
        session.close()