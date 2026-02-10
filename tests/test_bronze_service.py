"""
Tests pour Bronze Service - Extraction de données
"""
import pytest
import pandas as pd
from datetime import datetime
from unittest.mock import patch, MagicMock
from services.bronze_service import (
    extract_mt5_data,
    extract_yahoo_data,
    extract_eurostat_data
)



@pytest.mark.unit
@pytest.mark.bronze
def test_extract_mt5_data_valid_range(temp_parquet_file):
    """Test extraction MT5 avec dates valides"""
    with patch('services.bronze_service.import_data') as mock_import:
        mock_import.return_value = {
            'time': ['2024-01-01 00:00:00', '2024-01-01 00:15:00'],
            'open': [1.08, 1.081],
            'high': [1.082, 1.083],
            'low': [1.079, 1.080],
            'close': [1.081, 1.082],
            'tick_volume': [500, 600]
        }

        result = extract_mt5_data(start='2024-01-01', end='2024-01-31')

        assert result is not None
        assert result.endswith('.parquet')
        mock_import.assert_called_once()


@pytest.mark.unit
@pytest.mark.bronze
def test_extract_mt5_data_invalid_range():
    """Test extraction avec dates invalides (end < start)"""
    with patch('services.bronze_service.import_data') as mock_import:
        mock_import.side_effect = ValueError("End date must be after start date")

        with pytest.raises(ValueError):
            extract_mt5_data(start='2024-02-01', end='2024-01-01')


@pytest.mark.unit
@pytest.mark.bronze
def test_extract_mt5_data_empty_result():
    """Test extraction qui retourne aucune donnée"""
    with patch('services.bronze_service.import_data') as mock_import:
        mock_import.return_value = {
            'time': [],
            'open': [],
            'high': [],
            'low': [],
            'close': [],
            'tick_volume': []
        }

        result = extract_mt5_data(start='2024-01-01', end='2024-01-02')

        assert result is not None



@pytest.mark.unit
@pytest.mark.bronze
def test_extract_yahoo_data_valid(mock_vault_client):
    """Test extraction Yahoo Finance avec dates valides"""
    with patch('services.bronze_service.YahooFinanceClient') as MockClient:
        mock_instance = MockClient.return_value
        df_spx = pd.DataFrame({
            'time': pd.date_range('2024-01-01', periods=5, tz='UTC'),
            'close': [4500.0]*5
        }).set_index('time')
        df_dxy = pd.DataFrame({
            'time': pd.date_range('2024-01-01', periods=5, tz='UTC'),
            'close': [103.0]*5
        }).set_index('time')

        mock_instance.get_macro_context.return_value = {
            'spx': df_spx,
            'dxy': df_dxy,
        }

        result = extract_yahoo_data(
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 5)
        )

        assert isinstance(result, dict)
        assert 'spx' in result or len(result) > 0


@pytest.mark.unit
@pytest.mark.bronze
def test_extract_yahoo_data_api_error(mock_vault_client):
    """Test gestion erreur API Yahoo"""
    with patch('services.bronze_service.YahooFinanceClient') as MockClient:
        mock_instance = MockClient.return_value
        mock_instance.get_macro_context.side_effect = Exception("API Error")

        with pytest.raises(Exception):
            extract_yahoo_data(
                start=datetime(2024, 1, 1),
                end=datetime(2024, 1, 5)
            )



@pytest.mark.unit
@pytest.mark.bronze
def test_extract_eurostat_data_valid(mock_vault_client):
    """Test extraction Eurostat avec date valide"""
    with patch('services.bronze_service.EurostatClient') as MockClient:
        mock_instance = MockClient.return_value
        mock_instance.extract_all_documents.return_value = {
            'pib': pd.DataFrame({
                'time': pd.date_range('2024-01-01', periods=3, freq='Q', tz='UTC'),
                'eurozone_pib': [1.5, 1.6, 1.7]
            }),
            'cpi': pd.DataFrame({
                'time': pd.date_range('2024-01-01', periods=3, freq='M', tz='UTC'),
                'eurozone_cpi': [2.1, 2.2, 2.3]
            }),
            'events': pd.DataFrame({
                'time': pd.date_range('2024-01-01', periods=5, tz='UTC'),
                'event': ['Event A', 'Event B', 'Event C', 'Event D', 'Event E']
            }),
        }

        result = extract_eurostat_data(start=datetime(2024, 1, 1))

        assert isinstance(result, dict)
        assert 'pib' in result or 'cpi' in result or 'events' in result


@pytest.mark.integration
@pytest.mark.bronze
@pytest.mark.slow
def test_extract_pipeline_complete(mock_vault_client):
    """Test du pipeline complet d'extraction (intégration)"""
    with patch('services.bronze_service.import_data') as mock_mt5, \
         patch('services.bronze_service.YahooFinanceClient') as mock_yahoo, \
         patch('services.bronze_service.EurostatClient') as mock_eurostat:

        mock_mt5.return_value = {'time': ['2024-01-01'], 'close': [1.08]}

        mock_yahoo_instance = mock_yahoo.return_value
        df_spx = pd.DataFrame({
            'time': pd.date_range('2024-01-01', periods=5, tz='UTC'),
            'close': [4500.0]*5
        }).set_index('time')
        mock_yahoo_instance.get_macro_context.return_value = {
            'spx': df_spx
        }

        mock_eurostat_instance = mock_eurostat.return_value
        mock_eurostat_instance.extract_all_documents.return_value = {
            'events': pd.DataFrame({
                'time': pd.date_range('2024-01-01', periods=5, tz='UTC'),
                'event': ['Event 1', 'Event 2', 'Event 3', 'Event 4', 'Event 5']
            })
        }

        mt5_result = extract_mt5_data('2024-01-01', '2024-01-31')
        yahoo_result = extract_yahoo_data(
            datetime(2024, 1, 1),
            datetime(2024, 1, 31)
        )
        eurostat_result = extract_eurostat_data(datetime(2024, 1, 1))

        assert mt5_result is not None
        assert yahoo_result is not None
        assert eurostat_result is not None
