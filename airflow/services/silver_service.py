"""
Silver Layer Service - Transformation des features
Charge les .parquet Bronze, fait le merge et feature engineering,
retourne un .parquet transformé (pas de load DB ici)
"""

from datetime import datetime
import pandas as pd
import os


def transform_features(mt5_parquet: str, stooq_parquets: dict, eurostat_parquets: dict):
    """
    Transforme les données Bronze (.parquet) en features Silver (.parquet)

    Workflow:
    1. Charge les .parquet Bronze
    2. Merge et harmonisation (resample multi-horizon)
    3. Feature engineering
    4. Sauvegarde en .parquet transformé

    Args:
        mt5_parquet: Chemin du fichier MT5
        stooq_parquets: Dict {symbole: chemin}
        eurostat_parquets: Dict {type: chemin}

    Returns:
        str: Chemin du fichier .parquet transformé
    """
    print("[SILVER] Début transformation features...")

    # 1. Charger MT5 (base M15)
    df_mt5 = _load_mt5_parquet(mt5_parquet)

    # 2. Merge Stooq (daily → M15)
    df_mt5 = _merge_stooq_parquets(df_mt5, stooq_parquets)

    # 3. Merge Eurostat (monthly/quarterly → M15)
    df_mt5 = _merge_eurostat_parquets(df_mt5, eurostat_parquets)

    # 4. Feature Engineering
    df_mt5 = apply_feature_engineering(df_mt5)

    # 5. Nettoyage
    df_mt5 = df_mt5.dropna(subset=['close', 'open', 'high', 'low'])
    df_mt5 = df_mt5.ffill().fillna(0)

    print(f"[SILVER] ✓ {len(df_mt5)} lignes après transformation")

    # 6. Sauvegarde en .parquet
    output_path = "data/processed/eurusd_features.parquet"
    os.makedirs("data/processed", exist_ok=True)
    df_mt5.to_parquet(output_path)
    print(f"[SILVER] ✅ Features sauvegardées: {output_path}")

    return output_path


def _load_mt5_parquet(parquet_path: str) -> pd.DataFrame:
    """Charge les données MT5 depuis .parquet"""
    print(f"[SILVER] 📊 Chargement MT5 depuis {parquet_path}...")

    df = pd.read_parquet(parquet_path)

    if 'time' not in df.columns:
        df = df.reset_index()

    df['time'] = pd.to_datetime(df['time'], utc=True)
    df = df.set_index('time').sort_index()

    print(f"[SILVER]   ✓ {len(df)} lignes MT5, période {df.index.min()} → {df.index.max()}")

    return df


def _merge_stooq_parquets(df_mt5: pd.DataFrame, stooq_parquets: dict) -> pd.DataFrame:
    """Merge les données Stooq (daily → M15)"""
    print("[SILVER] 🌍 Merge Stooq...")

    for symbol, path in stooq_parquets.items():
        if not os.path.exists(path):
            print(f"[SILVER]   ⚠ {symbol} - fichier introuvable: {path}")
            continue

        try:
            df_symbol = pd.read_parquet(path)

            # Gestion de l'index
            if df_symbol.index.name == 'time' or 'time' not in df_symbol.columns:
                df_symbol = df_symbol.reset_index()

            df_symbol['time'] = pd.to_datetime(df_symbol['time'], utc=True)
            df_symbol = df_symbol.set_index('time').sort_index()

            # Sélectionner les colonnes OHLCV (case-insensitive)
            columns_map = {}
            for col in df_symbol.columns:
                col_lower = col.lower()
                if col_lower in ['open', 'high', 'low', 'close', 'volume']:
                    columns_map[col] = col_lower

            df_symbol = df_symbol.rename(columns=columns_map)
            available_cols = [c for c in ['open', 'high', 'low', 'close', 'volume'] if c in df_symbol.columns]

            if not available_cols:
                print(f"[SILVER]   ⚠ {symbol} - aucune colonne OHLCV trouvée")
                continue

            # Resample daily → M15
            df_resampled = df_symbol[available_cols].resample('15min').ffill()
            df_resampled.columns = [f"{symbol.lower()}_{col}" for col in df_resampled.columns]

            # Merge avec MT5
            df_mt5 = df_mt5.merge(df_resampled, left_index=True, right_index=True, how='left')
            print(f"[SILVER]   ✓ {symbol.upper()} mergé ({len(df_resampled.columns)} colonnes)")

        except Exception as e:
            print(f"[SILVER]   ⚠ Erreur {symbol}: {e}")

    return df_mt5


def _merge_eurostat_parquets(df_mt5: pd.DataFrame, eurostat_parquets: dict) -> pd.DataFrame:
    """Merge les données Eurostat (monthly/quarterly → M15)"""
    print("[SILVER] 📈 Merge Eurostat...")

    # PIB
    if 'pib' in eurostat_parquets and os.path.exists(eurostat_parquets['pib']):
        try:
            df_pib = pd.read_parquet(eurostat_parquets['pib'])

            if df_pib.index.name in ['TIME_PERIOD', 'time']:
                df_pib = df_pib.reset_index()

            # La première colonne est le temps
            time_col = df_pib.columns[0]
            df_pib['time'] = pd.to_datetime(df_pib[time_col], utc=True)
            df_pib = df_pib.set_index('time').sort_index()

            # Resample → M15
            df_resampled = df_pib[['eurozone_pib']].resample('15min').ffill()

            # Merge
            df_mt5 = df_mt5.merge(df_resampled, left_index=True, right_index=True, how='left')
            print(f"[SILVER]   ✓ PIB mergé")
        except Exception as e:
            print(f"[SILVER]   ⚠ Erreur PIB: {e}")

    # CPI
    if 'cpi' in eurostat_parquets and os.path.exists(eurostat_parquets['cpi']):
        try:
            df_cpi = pd.read_parquet(eurostat_parquets['cpi'])

            if df_cpi.index.name in ['TIME_PERIOD', 'time']:
                df_cpi = df_cpi.reset_index()

            time_col = df_cpi.columns[0]
            df_cpi['time'] = pd.to_datetime(df_cpi[time_col], utc=True)
            df_cpi = df_cpi.set_index('time').sort_index()

            # Resample → M15
            df_resampled = df_cpi[['eurozone_cpi']].resample('15min').ffill()

            # Merge
            df_mt5 = df_mt5.merge(df_resampled, left_index=True, right_index=True, how='left')
            print(f"[SILVER]   ✓ CPI mergé")
        except Exception as e:
            print(f"[SILVER]   ⚠ Erreur CPI: {e}")

    # Events
    if 'events' in eurostat_parquets and os.path.exists(eurostat_parquets['events']):
        try:
            df_events = pd.read_parquet(eurostat_parquets['events'])
            df_events['time'] = pd.to_datetime(df_events['time'], utc=True)
            df_events = df_events.set_index('time').sort_index()

            # Dernier événement connu (forward-fill)
            df_mt5["event_title"] = df_events["title"].reindex(df_mt5.index, method="ffill")
            df_mt5["event_impact"] = df_events["impact"].reindex(df_mt5.index, method="ffill")
            print(f"[SILVER]   ✓ Événements économiques mergés")
        except Exception as e:
            print(f"[SILVER]   ⚠ Erreur événements: {e}")

    return df_mt5


def apply_feature_engineering(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applique le feature engineering multi-horizon

    Args:
        df: DataFrame avec données brutes

    Returns:
        DataFrame avec features calculées
    """
    print("[SILVER] 🔧 Feature Engineering...")

    # MT5 Features (microstructure)
    df = _add_mt5_features(df)

    # Stooq Features (régime de marché)
    df = _add_stooq_features(df)

    # Eurostat Features (fondamentaux)
    df = _add_eurostat_features(df)

    # Features composites
    df = _add_composite_features(df)

    return df


def _add_mt5_features(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute les features MT5 (microstructure)"""
    df["close_diff"] = df["close"].diff()
    df["close_return"] = df["close"].pct_change()
    df["high_low_range"] = df["high"] - df["low"]
    df["volatility_1h"] = df["close"].rolling(4).std()
    df["volatility_4h"] = df["close"].rolling(16).std()
    df["momentum_15m"] = df["close"] - df["close"].shift(1)
    df["momentum_1h"] = df["close"] - df["close"].shift(4)
    df["momentum_4h"] = df["close"] - df["close"].shift(16)
    df["body"] = df["close"] - df["open"]
    df["upper_shadow"] = df["high"] - df[["open", "close"]].max(axis=1)
    df["lower_shadow"] = df[["open", "close"]].min(axis=1) - df["low"]
    return df


def _add_stooq_features(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute les features Stooq (régime de marché)"""
    if 'dxy_close' in df.columns:
        df["dxy_trend_1h"] = df["dxy_close"].pct_change(4)
        df["dxy_trend_4h"] = df["dxy_close"].pct_change(16)
        df["dxy_strength"] = (df["dxy_close"] - df["dxy_close"].rolling(96).mean()) / df["dxy_close"].rolling(96).std()

    if 'vix_close' in df.columns:
        df["vix_level"] = df["vix_close"]
        df["vix_change"] = df["vix_close"].pct_change(4)
        df["market_stress"] = (df["vix_close"] > 20).astype(int)

    if 'spx_close' in df.columns:
        df["spx_trend"] = df["spx_close"].pct_change(4)
        df["risk_on"] = (df["spx_trend"] > 0).astype(int)

    if 'gold_close' in df.columns:
        df["gold_trend"] = df["gold_close"].pct_change(4)
        df["safe_haven"] = (df["gold_trend"] > 0).astype(int)

    return df


def _add_eurostat_features(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute les features Eurostat (fondamentaux)"""
    if 'eurozone_pib' in df.columns:
        df["pib_change"] = df["eurozone_pib"].pct_change().fillna(0)
        df["pib_growth"] = (df["pib_change"] > 0).astype(int)

    if 'eurozone_cpi' in df.columns:
        df["cpi_change"] = df["eurozone_cpi"].pct_change().fillna(0)
        df["inflation_pressure"] = (df["cpi_change"] > 0.02).astype(int)

    # Event impact
    if 'event_impact' in df.columns:
        impact_map = {"High": 3, "Medium": 2, "Low": 1}
        df["event_impact_score"] = df["event_impact"].map(impact_map).fillna(0).astype(int)

    return df


def _add_composite_features(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute les features composites (multi-horizon)"""
    # Alignement macro/micro
    if 'dxy_trend_1h' in df.columns and 'close_return' in df.columns:
        df["macro_micro_aligned"] = ((df["close_return"] > 0) & (df["dxy_trend_1h"] < 0)).astype(int)

    # Biais directionnel EUR
    if 'pib_growth' in df.columns and 'risk_on' in df.columns:
        df["euro_strength_bias"] = (df["pib_growth"] * df["risk_on"]).astype(int)

    return df
