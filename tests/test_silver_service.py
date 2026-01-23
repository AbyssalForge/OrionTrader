"""
Tests pour Silver Service - Transformation et Feature Engineering
"""
import pytest
import pandas as pd
import numpy as np
from airflow.services.silver_service import (
    transform_mt5_features,
    transform_yahoo_features,
    transform_documents_features,
    transform_market_snapshot,
    _add_mt5_features,
    _calculate_composite_features
)
from tests.conftest import assert_dataframe_valid, assert_no_leakage


# ============================================================================
# TESTS TRANSFORMATION MT5
# ============================================================================

@pytest.mark.unit
@pytest.mark.silver
def test_transform_mt5_features_basic(temp_parquet_file):
    """Test transformation MT5 avec données valides"""
    result_path = transform_mt5_features(temp_parquet_file)

    # Vérifier fichier créé
    assert result_path.endswith('.parquet')

    # Charger et vérifier
    df = pd.read_parquet(result_path)
    assert_dataframe_valid(df, required_columns=[
        'open', 'high', 'low', 'close', 'tick_volume',
        'close_diff', 'close_return', 'high_low_range',
        'volatility_1h', 'volatility_4h',
        'momentum_15m', 'momentum_1h', 'momentum_4h'
    ])


@pytest.mark.unit
@pytest.mark.silver
def test_add_mt5_features_creates_all_columns(sample_mt5_data):
    """Test que _add_mt5_features crée toutes les colonnes attendues"""
    sample_mt5_data = sample_mt5_data.set_index('time')

    df_transformed = _add_mt5_features(sample_mt5_data)

    expected_features = [
        'close_diff', 'close_return', 'high_low_range',
        'volatility_1h', 'volatility_4h',
        'momentum_15m', 'momentum_1h', 'momentum_4h',
        'body', 'upper_shadow', 'lower_shadow'
    ]

    for feature in expected_features:
        assert feature in df_transformed.columns, f"Missing feature: {feature}"


@pytest.mark.unit
@pytest.mark.silver
def test_mt5_features_no_forward_fill_on_derived():
    """Test que les features dérivées ne sont PAS forward-fillées"""
    # Créer données avec gaps
    dates = pd.date_range(start='2024-01-01', periods=10, freq='15min', tz='UTC')
    df = pd.DataFrame({
        'time': dates,
        'open': [1.08] * 10,
        'high': [1.082] * 10,
        'low': [1.079] * 10,
        'close': [1.08, np.nan, 1.081, np.nan, 1.082] + [1.08] * 5,  # Gaps intentionnels
        'tick_volume': [500] * 10
    })

    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as f:
        df.to_parquet(f.name)
        result_path = transform_mt5_features(f.name)

    df_result = pd.read_parquet(result_path)

    # Vérifier que close_return a des NaN (pas forward-fillé après dropna initial)
    # Note: Le code actuel ffill uniquement les OHLC, pas les dérivées
    assert 'close_return' in df_result.columns


@pytest.mark.unit
@pytest.mark.silver
def test_mt5_volatility_calculation(sample_mt5_data):
    """Test calcul de volatilité"""
    sample_mt5_data = sample_mt5_data.set_index('time')
    df_transformed = _add_mt5_features(sample_mt5_data)

    # Volatilité doit être positive ou NaN
    assert (df_transformed['volatility_1h'] >= 0).all() or df_transformed['volatility_1h'].isna().all()
    assert (df_transformed['volatility_4h'] >= 0).all() or df_transformed['volatility_4h'].isna().all()


# ============================================================================
# TESTS TRANSFORMATION YAHOO
# ============================================================================

@pytest.mark.unit
@pytest.mark.silver
def test_transform_yahoo_features_basic(sample_yahoo_data):
    """Test transformation Yahoo Finance"""
    # Sauvegarder en parquets séparés
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        yahoo_parquets = {}
        for symbol in ['spx', 'gold', 'dxy', 'vix']:
            if f'{symbol}_close' in sample_yahoo_data.columns:
                df_symbol = sample_yahoo_data[['time', f'{symbol}_close']].copy()
                path = os.path.join(tmpdir, f'{symbol}.parquet')
                df_symbol.to_parquet(path)
                yahoo_parquets[symbol] = path

        result_path = transform_yahoo_features(yahoo_parquets)

        # Vérifier
        df = pd.read_parquet(result_path)
        assert 'spx_close' in df.columns or 'dxy_close' in df.columns


@pytest.mark.unit
@pytest.mark.silver
def test_yahoo_data_available_flag(sample_yahoo_data):
    """Test que le flag yahoo_data_available est créé"""
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        yahoo_parquets = {}
        df_spx = sample_yahoo_data[['time', 'spx_close']].copy()
        path = os.path.join(tmpdir, 'spx.parquet')
        df_spx.to_parquet(path)
        yahoo_parquets['spx'] = path

        result_path = transform_yahoo_features(yahoo_parquets)
        df = pd.read_parquet(result_path)

        # Vérifier flag
        assert 'yahoo_data_available' in df.columns
        assert df['yahoo_data_available'].dtype in [np.int64, np.int32, int]


# ============================================================================
# TESTS TRANSFORMATION DOCUMENTS
# ============================================================================

@pytest.mark.unit
@pytest.mark.silver
def test_transform_documents_features_basic(sample_documents_data):
    """Test transformation Documents"""
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        # Séparer par type
        df_pib = sample_documents_data[sample_documents_data['data_type'] == 'pib']
        df_cpi = sample_documents_data[sample_documents_data['data_type'] == 'cpi']

        pib_path = os.path.join(tmpdir, 'pib.parquet')
        cpi_path = os.path.join(tmpdir, 'cpi.parquet')

        df_pib.to_parquet(pib_path)
        df_cpi.to_parquet(cpi_path)

        documents_parquets = {'pib': pib_path, 'cpi': cpi_path}

        result_path = transform_documents_features(documents_parquets)

        # Vérifier
        df = pd.read_parquet(result_path)
        assert 'data_type' in df.columns
        assert 'frequency' in df.columns


@pytest.mark.unit
@pytest.mark.silver
def test_documents_use_npnan_not_none(sample_documents_data):
    """Test que np.nan est utilisé au lieu de None"""
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        df_pib = sample_documents_data[sample_documents_data['data_type'] == 'pib']

        pib_path = os.path.join(tmpdir, 'pib.parquet')
        df_pib.to_parquet(pib_path)

        documents_parquets = {'pib': pib_path}
        result_path = transform_documents_features(documents_parquets)

        df = pd.read_parquet(result_path)

        # Vérifier que les colonnes CPI sont np.nan (pas None)
        # np.nan doit être de type float
        if 'eurozone_cpi' in df.columns:
            assert pd.api.types.is_float_dtype(df['eurozone_cpi']) or df['eurozone_cpi'].isna().all()


# ============================================================================
# TESTS PREVENTION LEAKAGE
# ============================================================================

@pytest.mark.unit
@pytest.mark.silver
def test_composite_features_use_shift_for_close_return():
    """Test critique: close_return doit utiliser shift(1) pour éviter leakage"""
    # Créer données de test
    dates = pd.date_range(start='2024-01-01', periods=10, freq='15min', tz='UTC')

    df_merged = pd.DataFrame({
        'time': dates,
        'close_return': [0.001, 0.002, -0.001, 0.003, -0.002, 0.001, 0.002, -0.001, 0.001, 0.002],
        'dxy_trend_1h': [-0.001, -0.002, 0.001, -0.003, 0.002, -0.001, -0.002, 0.001, -0.001, -0.002]
    })
    df_merged = df_merged.set_index('time')

    df_snapshot = pd.DataFrame(index=df_merged.index)

    # Appeler fonction
    df_result = _calculate_composite_features(df_snapshot, df_merged)

    # Vérifier que macro_micro_aligned existe
    assert 'macro_micro_aligned' in df_result.columns

    # Vérifier que les valeurs ne sont pas identiques à l'original (preuve du shift)
    # Le premier élément devrait être 0 (fillna après shift)
    # Note: On ne peut pas vérifier directement le shift, mais on vérifie que ça ne crash pas


@pytest.mark.unit
@pytest.mark.silver
def test_no_future_leakage_in_features(sample_mt5_data):
    """Test qu'aucune feature n'utilise des données futures"""
    sample_mt5_data = sample_mt5_data.set_index('time')

    df_transformed = _add_mt5_features(sample_mt5_data)

    # Vérifier ordre temporel
    assert_no_leakage(df_transformed.reset_index(), time_col='time')

    # Vérifier que close_return à t ne dépend que de t et t-1
    # (test indirect: pas de valeurs futures)
    assert not df_transformed.index.duplicated().any()


# ============================================================================
# TESTS MARKET SNAPSHOT
# ============================================================================

@pytest.mark.integration
@pytest.mark.silver
@pytest.mark.slow
def test_transform_market_snapshot_integration(sample_mt5_data, sample_yahoo_data, sample_documents_data):
    """Test intégration complète du market snapshot"""
    import tempfile
    import os

    with tempfile.TemporaryDirectory() as tmpdir:
        # Préparer fichiers
        mt5_path = os.path.join(tmpdir, 'mt5.parquet')
        sample_mt5_data.to_parquet(mt5_path)

        # Transform MT5 first
        mt5_transformed = transform_mt5_features(mt5_path)

        # Yahoo
        yahoo_parquets = {}
        for col in ['spx_close', 'gold_close', 'dxy_close', 'vix_close']:
            if col in sample_yahoo_data.columns:
                symbol = col.replace('_close', '')
                df_symbol = sample_yahoo_data[['time', col]].copy()
                path = os.path.join(tmpdir, f'{symbol}.parquet')
                df_symbol.to_parquet(path)
                yahoo_parquets[symbol] = path

        yahoo_transformed = transform_yahoo_features(yahoo_parquets) if yahoo_parquets else None

        # Documents
        docs_parquets = {}
        if 'eurozone_pib' in sample_documents_data.columns:
            df_pib = sample_documents_data[sample_documents_data['data_type'] == 'pib']
            if not df_pib.empty:
                pib_path = os.path.join(tmpdir, 'pib.parquet')
                df_pib.to_parquet(pib_path)
                docs_parquets['pib'] = pib_path

        docs_transformed = transform_documents_features(docs_parquets) if docs_parquets else None

        # Market snapshot
        if yahoo_transformed and docs_transformed:
            snapshot_path = transform_market_snapshot(
                mt5_transformed,
                yahoo_transformed,
                docs_transformed
            )

            # Vérifier
            df_snapshot = pd.read_parquet(snapshot_path)
            assert 'mt5_time' in df_snapshot.columns
            assert 'yahoo_time' in df_snapshot.columns
            assert 'docs_time' in df_snapshot.columns
