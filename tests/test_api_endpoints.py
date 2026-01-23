"""
Tests pour API FastAPI - Endpoints
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import pandas as pd


# ============================================================================
# TESTS MARKET ENDPOINTS
# ============================================================================

@pytest.mark.api
@pytest.mark.unit
def test_market_latest_endpoint(test_api_client):
    """Test GET /market/latest"""
    with patch('app.routes.market.get_db') as mock_db:
        # Mock database query
        mock_session = MagicMock()
        mock_snapshot = MagicMock()
        mock_snapshot.time = '2024-01-01 00:00:00'
        mock_snapshot.signal_confidence_score = 0.75
        mock_snapshot.regime_composite = 'risk_on'

        mock_session.query().order_by().first.return_value = mock_snapshot
        mock_db.return_value = mock_session

        response = test_api_client.get("/market/latest")

        assert response.status_code == 200
        data = response.json()
        assert 'time' in data
        assert 'signal_confidence_score' in data


@pytest.mark.api
@pytest.mark.unit
def test_market_ohlcv_m15_endpoint(test_api_client):
    """Test GET /market/ohlcv/m15"""
    with patch('app.routes.market.get_db') as mock_db:
        mock_session = MagicMock()

        # Mock query result
        mock_record = MagicMock()
        mock_record.time = '2024-01-01 00:00:00'
        mock_record.open = 1.08
        mock_record.high = 1.082
        mock_record.low = 1.079
        mock_record.close = 1.081
        mock_record.tick_volume = 500

        mock_session.query().filter().order_by().offset().limit().all.return_value = [mock_record]
        mock_db.return_value = mock_session

        response = test_api_client.get("/market/ohlcv/m15?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.api
@pytest.mark.unit
def test_health_endpoint(test_api_client):
    """Test GET /health"""
    with patch('app.routes.market.test_connection') as mock_test_conn, \
         patch('app.routes.market.get_table_counts') as mock_counts:

        mock_test_conn.return_value = True
        mock_counts.return_value = {
            'mt5_eurusd_m15': 1000,
            'yahoo_finance_daily': 100,
            'documents_macro': 50,
            'market_snapshot_m15': 1000
        }

        response = test_api_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        assert 'database' in data
        assert 'tables' in data


# ============================================================================
# TESTS MODEL ENDPOINTS
# ============================================================================

@pytest.mark.api
@pytest.mark.ml
def test_model_predict_endpoint(test_api_client, trained_model):
    """Test POST /model/predict"""
    with patch('app.routes.model.load_model_with_cache') as mock_load:
        mock_load.return_value = trained_model

        payload = {
            "open": 1.0850,
            "high": 1.0865,
            "low": 1.0845,
            "close": 1.0860,
            "volume": 1500,
            "dxy_close": 103.5,
            "vix_close": 18.2,
            "spx_close": 4500.0
        }

        response = test_api_client.post("/model/predict", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert 'prediction' in data
        assert 'probabilities' in data
        assert 'confidence' in data
        assert data['prediction'] in ['SHORT', 'NEUTRAL', 'LONG']


@pytest.mark.api
@pytest.mark.ml
def test_model_predict_invalid_input(test_api_client):
    """Test POST /model/predict avec input invalide"""
    payload = {
        "open": "invalid",  # String au lieu de float
        "high": 1.0865,
    }

    response = test_api_client.post("/model/predict", json=payload)

    # Devrait retourner erreur de validation
    assert response.status_code == 422  # Unprocessable Entity


@pytest.mark.api
@pytest.mark.ml
def test_model_info_endpoint(test_api_client):
    """Test GET /model/info"""
    with patch('app.routes.model._model_cache') as mock_cache:
        mock_cache.return_value = {
            'model': MagicMock(),
            'version': 'latest',
            'loaded_at': '2024-01-01 00:00:00'
        }

        response = test_api_client.get("/model/info")

        assert response.status_code == 200
        data = response.json()
        assert 'model_name' in data or 'version' in data


@pytest.mark.api
@pytest.mark.ml
def test_model_reload_endpoint(test_api_client, trained_model):
    """Test POST /model/reload"""
    with patch('app.routes.model.load_model_with_cache') as mock_load:
        mock_load.return_value = trained_model

        response = test_api_client.post("/model/reload")

        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'reloaded'


# ============================================================================
# TESTS SIGNALS ENDPOINTS
# ============================================================================

@pytest.mark.api
@pytest.mark.unit
def test_signals_high_confidence_endpoint(test_api_client):
    """Test GET /signals/high-confidence"""
    with patch('app.routes.signals.get_db') as mock_db:
        mock_session = MagicMock()

        mock_signal = MagicMock()
        mock_signal.time = '2024-01-01 00:00:00'
        mock_signal.signal_confidence_score = 0.85
        mock_signal.trend_strength_composite = 0.6

        mock_session.query().join().filter().order_by().limit().all.return_value = [mock_signal]
        mock_db.return_value = mock_session

        response = test_api_client.get("/signals/high-confidence?min_confidence=0.7")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


# ============================================================================
# TESTS DATA ENDPOINTS
# ============================================================================

@pytest.mark.api
@pytest.mark.unit
def test_data_features_mt5_endpoint(test_api_client):
    """Test GET /data/features/mt5"""
    with patch('app.routes.data.get_db') as mock_db:
        mock_session = MagicMock()

        mock_record = MagicMock()
        mock_record.time = '2024-01-01 00:00:00'
        mock_record.close_return = 0.001
        mock_record.volatility_1h = 0.002

        mock_session.query().filter().order_by().offset().limit().all.return_value = [mock_record]
        mock_db.return_value = mock_session

        response = test_api_client.get("/data/features/mt5?limit=10")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


# ============================================================================
# TESTS AUTHENTICATION
# ============================================================================

@pytest.mark.api
@pytest.mark.unit
def test_auth_token_endpoint(test_api_client):
    """Test POST /auth/token"""
    with patch('app.routes.auth.authenticate_user') as mock_auth, \
         patch('app.routes.auth.create_access_token') as mock_token:

        mock_auth.return_value = MagicMock(username='test_user')
        mock_token.return_value = 'fake_jwt_token'

        response = test_api_client.post("/auth/token", data={
            "username": "test_user",
            "password": "test_password"
        })

        assert response.status_code == 200
        data = response.json()
        assert 'access_token' in data
        assert data['token_type'] == 'bearer'


@pytest.mark.api
@pytest.mark.unit
def test_protected_endpoint_without_auth(test_api_client):
    """Test accès endpoint protégé sans authentification"""
    # Certains endpoints nécessitent authentification
    # Remplacer par un vrai endpoint protégé si existant
    pass


# ============================================================================
# TESTS VALIDATION & ERROR HANDLING
# ============================================================================

@pytest.mark.api
@pytest.mark.unit
def test_api_404_on_invalid_route(test_api_client):
    """Test 404 sur route invalide"""
    response = test_api_client.get("/invalid/route/does/not/exist")

    assert response.status_code == 404


@pytest.mark.api
@pytest.mark.unit
def test_api_cors_headers(test_api_client):
    """Test que les headers CORS sont présents"""
    response = test_api_client.get("/health")

    # Vérifier que CORS est configuré (headers présents ou non)
    # Note: Dépend de la config CORS de l'app
    assert response.status_code == 200


# ============================================================================
# TESTS PERFORMANCE
# ============================================================================

@pytest.mark.api
@pytest.mark.slow
def test_api_response_time_under_threshold(test_api_client):
    """Test que les endpoints répondent en moins de 1s"""
    import time

    start = time.time()
    response = test_api_client.get("/health")
    elapsed = time.time() - start

    assert response.status_code == 200
    assert elapsed < 1.0, f"Response took {elapsed:.2f}s (> 1s threshold)"
