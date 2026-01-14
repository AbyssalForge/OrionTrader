"""
Silver Layer Service v3.0 - Transformations séparées pour architecture 4 tables
Transforme chaque source indépendamment (pas de merge)
"""

from datetime import datetime
import pandas as pd
import os
import numpy as np


# ============================================================================
# TRANSFORMATION 1/4 - MT5
# ============================================================================

def transform_mt5_features(mt5_parquet: str) -> str:
    """
    Transforme les données MT5 uniquement

    Args:
        mt5_parquet: Chemin du fichier MT5 brut

    Returns:
        str: Chemin du fichier .parquet transformé
    """
    print("[SILVER/MT5] Transformation MT5...")

    # Charger MT5
    df = pd.read_parquet(mt5_parquet)

    if 'time' not in df.columns:
        df = df.reset_index()

    df['time'] = pd.to_datetime(df['time'], utc=True)
    df = df.set_index('time').sort_index()

    print(f"[SILVER/MT5]   Shape brute: {df.shape}")
    print(f"[SILVER/MT5]   Période: {df.index.min()} -> {df.index.max()}")

    # Feature engineering MT5
    df = _add_mt5_features(df)

    # Nettoyage
    df = df.dropna(subset=['close', 'open', 'high', 'low'])
    df = df.ffill()

    # Sauvegarde
    output_path = "data/processed/mt5_features.parquet"
    os.makedirs("data/processed", exist_ok=True)
    df.to_parquet(output_path)

    print(f"[SILVER/MT5] OK: {len(df)} lignes -> {output_path}")
    return output_path


def _add_mt5_features(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute features microstructure MT5"""
    print("[SILVER/MT5] Feature engineering MT5...")

    # Variations de prix
    df['close_diff'] = df['close'].diff()
    df['close_return'] = df['close'].pct_change()
    df['high_low_range'] = df['high'] - df['low']

    # Volatilité multi-horizon
    df['volatility_1h'] = df['close'].pct_change().rolling(4).std()   # 4 × 15min = 1h
    df['volatility_4h'] = df['close'].pct_change().rolling(16).std()  # 16 × 15min = 4h

    # Momentum multi-horizon
    df['momentum_15m'] = df['close'].pct_change(1)
    df['momentum_1h'] = df['close'].pct_change(4)
    df['momentum_4h'] = df['close'].pct_change(16)

    # Analyse chandelier
    df['body'] = (df['close'] - df['open']).abs()
    df['upper_shadow'] = df['high'] - df[['open', 'close']].max(axis=1)
    df['lower_shadow'] = df[['open', 'close']].min(axis=1) - df['low']

    print(f"[SILVER/MT5]   Features ajoutées: 11 colonnes")
    return df


# ============================================================================
# TRANSFORMATION 2/4 - YAHOO FINANCE
# ============================================================================

def transform_yahoo_features(yahoo_parquets: dict) -> str:
    """
    Transforme les données Yahoo Finance uniquement

    Args:
        yahoo_parquets: Dict {symbole: chemin}

    Returns:
        str: Chemin du fichier .parquet transformé
    """
    print("[SILVER/YAHOO] Transformation Yahoo Finance...")

    # Charger tous les symboles Yahoo
    dfs = {}
    for symbol, path in yahoo_parquets.items():
        if not os.path.exists(path):
            print(f"[SILVER/YAHOO]   ATTENTION: {symbol} - fichier introuvable")
            continue

        df_symbol = pd.read_parquet(path)

        if df_symbol.index.name == 'time' or 'time' not in df_symbol.columns:
            df_symbol = df_symbol.reset_index()

        df_symbol['time'] = pd.to_datetime(df_symbol['time'], utc=True)

        # IMPORTANT: Normaliser les timestamps à minuit (00:00:00) pour éviter les doublons
        # Yahoo Finance peut renvoyer des timestamps avec différentes heures (12:00, 16:00, etc.)
        df_symbol['time'] = df_symbol['time'].dt.normalize()

        df_symbol = df_symbol.set_index('time').sort_index()

        # Si des doublons existent après normalisation, garder le dernier
        df_symbol = df_symbol[~df_symbol.index.duplicated(keep='last')]

        # Sélectionner close
        if 'close' in df_symbol.columns:
            dfs[symbol] = df_symbol[['close']].rename(columns={'close': f'{symbol}_close'})

    # Merger tous les symboles avec outer join (garder toutes les dates)
    df = pd.concat(dfs.values(), axis=1, join='outer')

    print(f"[SILVER/YAHOO]   Shape brute: {df.shape}")
    print(f"[SILVER/YAHOO]   Période: {df.index.min()} -> {df.index.max()}")
    print(f"[SILVER/YAHOO]   Actifs mergés: {len(dfs)}")

    # Feature engineering Yahoo
    df = _add_yahoo_features(df)

    # Nettoyage
    df = df.ffill().fillna(0)

    # Sauvegarde
    output_path = "data/processed/yahoo_features.parquet"
    os.makedirs("data/processed", exist_ok=True)
    df.to_parquet(output_path)

    print(f"[SILVER/YAHOO] OK: {len(df)} lignes -> {output_path}")
    return output_path


def _add_yahoo_features(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute features régime de marché"""
    print("[SILVER/YAHOO] Feature engineering Yahoo...")

    # S&P 500 - Risk appetite
    if 'spx_close' in df.columns:
        df['spx_trend'] = df['spx_close'].pct_change(5)
        df['risk_on'] = (df['spx_trend'] > 0).astype(int)

    # Gold - Safe haven
    if 'gold_close' in df.columns:
        df['gold_trend'] = df['gold_close'].pct_change(5)
        df['safe_haven'] = (df['gold_trend'] > 0).astype(int)

    # DXY - Dollar strength
    if 'dxy_close' in df.columns:
        df['dxy_trend_1h'] = df['dxy_close'].pct_change(1)
        df['dxy_trend_4h'] = df['dxy_close'].pct_change(4)
        ma_20 = df['dxy_close'].rolling(20).mean()
        df['dxy_strength'] = (df['dxy_close'] - ma_20) / ma_20

    # VIX - Market stress
    if 'vix_close' in df.columns:
        ma_20 = df['vix_close'].rolling(20).mean()
        df['vix_level'] = (df['vix_close'] - ma_20) / ma_20
        df['vix_change'] = df['vix_close'].pct_change()
        df['market_stress'] = (df['vix_close'] > 20).astype(int)

    print(f"[SILVER/YAHOO]   Features ajoutées: 10 colonnes")
    return df


# ============================================================================
# TRANSFORMATION 3/4 - DOCUMENTS MACRO
# ============================================================================

def transform_documents_features(documents_parquets: dict) -> str:
    """
    Transforme les données documents uniquement

    Args:
        documents_parquets: Dict {type: chemin}

    Returns:
        str: Chemin du fichier .parquet transformé
    """
    print("[SILVER/DOCS] Transformation Documents...")

    dfs = []

    # PIB
    if 'pib' in documents_parquets and os.path.exists(documents_parquets['pib']):
        df_pib = pd.read_parquet(documents_parquets['pib'])
        df_pib = _prepare_document_df(df_pib, 'pib', 'annual')
        df_pib = _add_pib_features(df_pib)
        dfs.append(df_pib)

    # CPI
    if 'cpi' in documents_parquets and os.path.exists(documents_parquets['cpi']):
        df_cpi = pd.read_parquet(documents_parquets['cpi'])
        df_cpi = _prepare_document_df(df_cpi, 'cpi', 'monthly')
        df_cpi = _add_cpi_features(df_cpi)
        dfs.append(df_cpi)

    # Events
    if 'events' in documents_parquets and os.path.exists(documents_parquets['events']):
        df_events = pd.read_parquet(documents_parquets['events'])
        df_events = _prepare_document_df(df_events, 'event', 'punctual')
        df_events = _add_event_features(df_events)
        dfs.append(df_events)

    # Concat tous les documents
    df = pd.concat(dfs, axis=0).sort_index()

    print(f"[SILVER/DOCS]   Shape: {df.shape}")
    print(f"[SILVER/DOCS]   Période: {df.index.min()} -> {df.index.max()}")

    # Sauvegarde
    output_path = "data/processed/documents_features.parquet"
    os.makedirs("data/processed", exist_ok=True)
    df.to_parquet(output_path)

    print(f"[SILVER/DOCS] OK: {len(df)} lignes -> {output_path}")
    return output_path


def _prepare_document_df(df: pd.DataFrame, data_type: str, frequency: str) -> pd.DataFrame:
    """Prépare un DataFrame document avec metadata"""
    if 'time' not in df.columns:
        df = df.reset_index()

    df['time'] = pd.to_datetime(df['time'], utc=True)
    df = df.set_index('time').sort_index()

    df['data_type'] = data_type
    df['frequency'] = frequency

    return df


def _add_pib_features(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute features PIB"""
    if 'eurozone_pib' in df.columns:
        df['pib_change'] = df['eurozone_pib'].pct_change()
        df['pib_growth'] = df['pib_change'].diff()

    # Colonnes CPI et Events à None pour compatibilité
    df['eurozone_cpi'] = None
    df['cpi_change'] = None
    df['inflation_pressure'] = None
    df['event_title'] = None
    df['event_impact'] = None
    df['event_impact_score'] = None

    return df


def _add_cpi_features(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute features CPI"""
    if 'eurozone_cpi' in df.columns:
        df['cpi_change'] = df['eurozone_cpi'].pct_change()
        df['inflation_pressure'] = (df['cpi_change'] > 0.02).astype(int)

    # Colonnes PIB et Events à None pour compatibilité
    df['eurozone_pib'] = None
    df['pib_change'] = None
    df['pib_growth'] = None
    df['event_title'] = None
    df['event_impact'] = None
    df['event_impact_score'] = None

    return df


def _add_event_features(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute features Events et score d'impact"""
    # Calculer event_impact_score si pas présent
    if 'event_impact' in df.columns and 'event_impact_score' not in df.columns:
        impact_map = {'high': 1.0, 'medium': 0.5, 'low': 0.1}
        df['event_impact_score'] = df['event_impact'].map(impact_map).fillna(0.0)

    # Colonnes PIB et CPI à None pour compatibilité
    df['eurozone_pib'] = None
    df['pib_change'] = None
    df['pib_growth'] = None
    df['eurozone_cpi'] = None
    df['cpi_change'] = None
    df['inflation_pressure'] = None

    return df


# ============================================================================
# TRANSFORMATION 4/4 - FEATURES COMPOSITES
# ============================================================================

def transform_market_snapshot(
    mt5_parquet: str,
    yahoo_parquet: str,
    documents_parquet: str
) -> str:
    """
    Calcule market snapshot avec toutes les features composites et foreign keys

    Args:
        mt5_parquet: Chemin features MT5
        yahoo_parquet: Chemin features Yahoo
        documents_parquet: Chemin features Documents

    Returns:
        str: Chemin du fichier .parquet transformé (market_snapshot_m15.parquet)
    """
    print("[SILVER/SNAPSHOT] Calcul market snapshot M15...")

    # Charger les 3 sources
    df_mt5 = pd.read_parquet(mt5_parquet)
    df_yahoo = pd.read_parquet(yahoo_parquet)
    df_docs = pd.read_parquet(documents_parquet)

    # Préparer pour merge_asof
    df_mt5_reset = df_mt5.reset_index()
    df_yahoo_reset = df_yahoo.reset_index()
    df_docs_reset = df_docs.reset_index()

    # Renommer les colonnes time avant le merge pour pouvoir les récupérer
    df_yahoo_reset = df_yahoo_reset.rename(columns={'time': 'yahoo_time'})
    df_docs_reset = df_docs_reset.rename(columns={'time': 'docs_time'})

    # Merger Yahoo (daily -> M15)
    df_merged = pd.merge_asof(
        df_mt5_reset.sort_values('time'),
        df_yahoo_reset.sort_values('yahoo_time'),
        left_on='time',
        right_on='yahoo_time',
        direction='backward'
    )

    # Merger Documents (monthly -> M15)
    df_merged = pd.merge_asof(
        df_merged.sort_values('time'),
        df_docs_reset.sort_values('docs_time'),
        left_on='time',
        right_on='docs_time',
        direction='backward'
    )

    # Créer DataFrame snapshot (garder time comme colonne pour l'instant)
    df_snapshot = pd.DataFrame()

    # ===== FOREIGN KEYS =====
    df_snapshot['time'] = df_merged['time']  # PK du snapshot (= timestamp M15)
    df_snapshot['mt5_time'] = df_merged['time']  # FK vers MT5 (même que time)
    df_snapshot['yahoo_time'] = df_merged['yahoo_time']  # FK vers Yahoo (backward fill)
    df_snapshot['docs_time'] = df_merged['docs_time']  # FK vers Documents (backward fill)

    # Set index pour les deux DataFrames (important pour alignement lors des calculs)
    df_snapshot = df_snapshot.set_index('time')
    df_merged = df_merged.set_index('time')

    # ===== FEATURES COMPOSITES MULTI-SOURCES =====
    df_snapshot = _calculate_composite_features(df_snapshot, df_merged)

    # ===== RÉGIMES ET CLASSIFICATIONS =====
    df_snapshot = _calculate_regimes(df_snapshot, df_merged)

    # ===== SCORES ET MÉTRIQUES =====
    df_snapshot = _calculate_scores(df_snapshot, df_merged)

    # ===== EVENT MANAGEMENT =====
    df_snapshot = _calculate_event_window(df_snapshot, df_merged)

    print(f"[SILVER/SNAPSHOT]   Shape: {df_snapshot.shape}")
    print(f"[SILVER/SNAPSHOT]   Colonnes: {list(df_snapshot.columns)}")

    # Sauvegarde
    output_path = "data/processed/market_snapshot_m15.parquet"
    os.makedirs("data/processed", exist_ok=True)
    df_snapshot.to_parquet(output_path)

    print(f"[SILVER/SNAPSHOT] OK: {len(df_snapshot)} lignes -> {output_path}")
    return output_path


def _calculate_composite_features(df_snapshot: pd.DataFrame, df_merged: pd.DataFrame) -> pd.DataFrame:
    """Calcule macro_micro_aligned et euro_strength_bias"""
    print("[SILVER/SNAPSHOT]   Calcul features composites...")

    # 1. macro_micro_aligned (DXY vs EUR/USD)
    if 'dxy_trend_1h' in df_merged.columns and 'close_return' in df_merged.columns:
        dxy_trend = df_merged['dxy_trend_1h'].fillna(0)
        eur_return = df_merged['close_return'].fillna(0)

        df_snapshot['macro_micro_aligned'] = np.where(
            (dxy_trend < 0) & (eur_return > 0), 1,
            np.where((dxy_trend > 0) & (eur_return < 0), -1, 0)
        )
    else:
        df_snapshot['macro_micro_aligned'] = 0

    # 2. euro_strength_bias (PIB + risk_on)
    if 'pib_change' in df_merged.columns and 'risk_on' in df_merged.columns:
        pib_change = df_merged['pib_change'].fillna(0)
        risk_on = df_merged['risk_on'].fillna(0)

        df_snapshot['euro_strength_bias'] = np.where(
            (pib_change > 0) & (risk_on == 1), 1,
            np.where((pib_change < 0) & (risk_on == 0), -1, 0)
        )
    else:
        df_snapshot['euro_strength_bias'] = 0

    return df_snapshot


def _calculate_regimes(df_snapshot: pd.DataFrame, df_merged: pd.DataFrame) -> pd.DataFrame:
    """Calcule regime_composite et volatility_regime"""
    print("[SILVER/SNAPSHOT]   Calcul régimes...")

    # 1. regime_composite (marché global)
    if 'vix_close' in df_merged.columns and 'risk_on' in df_merged.columns and 'safe_haven' in df_merged.columns:
        vix = df_merged['vix_close'].fillna(20)
        risk_on = df_merged['risk_on'].fillna(0)
        safe_haven = df_merged['safe_haven'].fillna(0)
        market_stress = df_merged['market_stress'].fillna(0)

        df_snapshot['regime_composite'] = 'neutral'
        df_snapshot.loc[(vix < 15) & (risk_on == 1), 'regime_composite'] = 'risk_on'
        df_snapshot.loc[(vix > 25) & (safe_haven == 1), 'regime_composite'] = 'risk_off'
        df_snapshot.loc[market_stress == 1, 'regime_composite'] = 'volatile'
    else:
        df_snapshot['regime_composite'] = 'neutral'

    # 2. volatility_regime (volatilité relative)
    if 'volatility_1h' in df_merged.columns:
        vol = df_merged['volatility_1h'].fillna(0)
        vol_ma = vol.rolling(100, min_periods=1).mean()
        vol_percentile = vol / vol_ma.replace(0, 1)

        df_snapshot['volatility_regime'] = 'normal'
        df_snapshot.loc[vol_percentile < 0.5, 'volatility_regime'] = 'low'
        df_snapshot.loc[vol_percentile > 1.5, 'volatility_regime'] = 'high'
    else:
        df_snapshot['volatility_regime'] = 'normal'

    return df_snapshot


def _calculate_scores(df_snapshot: pd.DataFrame, df_merged: pd.DataFrame) -> pd.DataFrame:
    """Calcule signal_confidence_score, signal_divergence_count, trend_strength_composite"""
    print("[SILVER/SNAPSHOT]   Calcul scores...")

    # 1. signal_divergence_count
    divergence_count = pd.Series(0, index=df_snapshot.index)

    if 'dxy_strength' in df_merged.columns and 'close_return' in df_merged.columns:
        dxy_strength = df_merged['dxy_strength'].fillna(0)
        close_return = df_merged['close_return'].fillna(0)
        divergence_count += ((dxy_strength > 0) & (close_return > 0)).astype(int)

    if 'risk_on' in df_merged.columns and 'safe_haven' in df_merged.columns:
        risk_on = df_merged['risk_on'].fillna(0)
        safe_haven = df_merged['safe_haven'].fillna(0)
        divergence_count += ((risk_on == 1) & (safe_haven == 1)).astype(int)

    if 'inflation_pressure' in df_merged.columns and 'pib_change' in df_merged.columns:
        inflation_pressure = df_merged['inflation_pressure'].fillna(0)
        pib_change = df_merged['pib_change'].fillna(0)
        divergence_count += ((inflation_pressure == 1) & (pib_change < 0)).astype(int)

    df_snapshot['signal_divergence_count'] = divergence_count

    # 2. signal_confidence_score
    score = pd.Series(0.0, index=df_snapshot.index)

    if 'macro_micro_aligned' in df_snapshot.columns:
        score += (df_snapshot['macro_micro_aligned'] != 0).astype(float) * 0.3

    if 'euro_strength_bias' in df_snapshot.columns:
        score += (df_snapshot['euro_strength_bias'] != 0).astype(float) * 0.3

    if 'volatility_4h' in df_merged.columns:
        vol_threshold = df_merged['volatility_4h'].quantile(0.75)
        score += (df_merged['volatility_4h'].fillna(999) < vol_threshold).astype(float) * 0.2

    score += (df_snapshot['signal_divergence_count'] == 0).astype(float) * 0.2

    df_snapshot['signal_confidence_score'] = score.clip(0, 1)

    # 3. trend_strength_composite
    if all(col in df_merged.columns for col in ['momentum_15m', 'momentum_1h', 'momentum_4h']):
        mom_15m = df_merged['momentum_15m'].fillna(0)
        mom_1h = df_merged['momentum_1h'].fillna(0)
        mom_4h = df_merged['momentum_4h'].fillna(0)

        df_snapshot['trend_strength_composite'] = (
            0.2 * mom_15m + 0.3 * mom_1h + 0.5 * mom_4h
        ).clip(-1, 1)
    else:
        df_snapshot['trend_strength_composite'] = 0.0

    return df_snapshot


def _calculate_event_window(df_snapshot: pd.DataFrame, df_merged: pd.DataFrame) -> pd.DataFrame:
    """Calcule event_window_active"""
    print("[SILVER/SNAPSHOT]   Calcul event windows...")

    if 'event_impact_score' in df_merged.columns:
        event_score = df_merged['event_impact_score'].fillna(0)
        df_snapshot['event_window_active'] = (event_score > 0.7)
    else:
        df_snapshot['event_window_active'] = False

    return df_snapshot
