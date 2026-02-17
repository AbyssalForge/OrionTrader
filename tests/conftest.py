"""
Configuration pytest - Fixtures partagées pour tous les tests
"""
import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent
airflow_path = project_root / "airflow"
if str(airflow_path) not in sys.path:
    sys.path.insert(0, str(airflow_path))

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import tempfile


@pytest.fixture
def sample_mt5_data():
    """Génère un DataFrame MT5 de test"""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='15min', tz='UTC')

    np.random.seed(42)
    data = {
        'time': dates,
        'open': 1.08 + np.random.randn(100) * 0.001,
        'high': 1.08 + np.random.randn(100) * 0.001 + 0.0005,
        'low': 1.08 + np.random.randn(100) * 0.001 - 0.0005,
        'close': 1.08 + np.random.randn(100) * 0.001,
        'tick_volume': np.random.randint(100, 1000, 100)
    }

    df = pd.DataFrame(data)
    df['high'] = df[['open', 'close', 'high']].max(axis=1)
    df['low'] = df[['open', 'close', 'low']].min(axis=1)

    return df


@pytest.fixture
def sample_yahoo_data():
    """Génère un DataFrame Yahoo Finance de test"""
    dates = pd.date_range(start='2024-01-01', periods=30, freq='D', tz='UTC')

    np.random.seed(42)
    data = {
        'time': dates,
        'spx_close': 4500 + np.random.randn(30) * 50,
        'gold_close': 2000 + np.random.randn(30) * 20,
        'dxy_close': 103 + np.random.randn(30) * 2,
        'vix_close': 18 + np.random.randn(30) * 3
    }

    return pd.DataFrame(data)


@pytest.fixture
def sample_documents_data():
    """Génère un DataFrame Documents de test"""
    dates = pd.date_range(start='2024-01-01', periods=12, freq='MS', tz='UTC')

    data = {
        'time': dates,
        'data_type': ['pib'] * 4 + ['cpi'] * 4 + ['event'] * 4,
        'frequency': ['monthly'] * 12,
        'eurozone_pib': [1.5, 1.6, 1.7, 1.6] + [np.nan] * 8,
        'eurozone_cpi': [np.nan] * 4 + [2.1, 2.2, 2.3, 2.2] + [np.nan] * 4,
    }

    return pd.DataFrame(data)


@pytest.fixture
def temp_parquet_file(sample_mt5_data):
    """Crée un fichier parquet temporaire"""
    with tempfile.NamedTemporaryFile(suffix='.parquet', delete=False) as f:
        sample_mt5_data.to_parquet(f.name)
        yield f.name

    if os.path.exists(f.name):
        os.remove(f.name)



@pytest.fixture(scope="session")
def test_db_engine():
    """Crée une base de données SQLite en mémoire pour les tests"""
    engine = create_engine("sqlite:///:memory:")
    yield engine
    engine.dispose()


@pytest.fixture
def test_db_session(test_db_engine):
    """Crée une session de base de données pour les tests"""
    from models.base import Base

    Base.metadata.create_all(test_db_engine)

    Session = sessionmaker(bind=test_db_engine)
    session = Session()

    yield session

    session.rollback()
    session.close()
    Base.metadata.drop_all(test_db_engine)



@pytest.fixture
def test_api_client(test_db_session, monkeypatch):
    """Client de test FastAPI avec authentification mockée"""
    from fastapi.testclient import TestClient
    from unittest.mock import MagicMock
    import sqlalchemy
    import sqlalchemy.orm

    fastapi_path = project_root / "fastapi"
    if str(fastapi_path) not in sys.path:
        sys.path.insert(0, str(fastapi_path))

    # Mock des imports optionnels pour les tests
    sys.modules['prometheus_fastapi_instrumentator'] = MagicMock()
    sys.modules['prometheus_client'] = MagicMock()

    # Mock de sqlalchemy.create_engine pour éviter l'import de psycopg2
    # et la vraie connexion à PostgreSQL lors de l'import de app.core.database
    mock_engine = MagicMock()
    mock_sessionmaker_class = MagicMock(return_value=MagicMock)

    monkeypatch.setattr(sqlalchemy, 'create_engine', lambda *args, **kwargs: mock_engine)
    monkeypatch.setattr(sqlalchemy.orm, 'sessionmaker', lambda *args, **kwargs: mock_sessionmaker_class)

    # Force reload des modules app.* pour qu'ils utilisent les mocks
    app_modules = [m for m in list(sys.modules.keys()) if m.startswith('app.')]
    for module_name in app_modules:
        del sys.modules[module_name]

    from app.main import app
    from app.core.auth import verify_api_token
    from app.core.dependencies import get_db
    from app.models.api_token import APIToken

    # Mock de l'authentification - retourne un token admin valide
    async def override_verify_api_token():
        return APIToken(
            token="test_token",
            name="Test API Key",
            is_active=True,
            created_at=datetime.now(),
            scopes="read,write,admin"  # Inclure admin pour les tests
        )

    # Mock de la base de données - retourne une session mockée
    mock_db_session = MagicMock()
    # La session mockée doit supporter query().filter().order_by().first() etc.
    mock_db_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
    mock_db_session.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

    def override_get_db():
        yield mock_db_session

    # Override les dépendances
    app.dependency_overrides[verify_api_token] = override_verify_api_token
    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    yield client

    # Nettoyer les overrides après les tests
    app.dependency_overrides.clear()



@pytest.fixture
def sample_training_data():
    """Génère des données d'entraînement de test"""
    np.random.seed(42)
    n_samples = 1000

    X = pd.DataFrame({
        'close_return': np.random.randn(n_samples) * 0.001,
        'volatility_1h': np.abs(np.random.randn(n_samples) * 0.002),
        'momentum_1h': np.random.randn(n_samples) * 0.001,
        'dxy_trend': np.random.randn(n_samples) * 0.005,
        'vix_close': np.clip(15 + np.random.randn(n_samples) * 5, 5, 80),
    })

    y = np.random.choice([-1, 0, 1], n_samples, p=[0.3, 0.4, 0.3])

    return X, y


@pytest.fixture
def trained_model(sample_training_data):
    """Entraîne un modèle simple pour les tests"""
    from lightgbm import LGBMClassifier

    X, y = sample_training_data

    model = LGBMClassifier(
        n_estimators=10,
        max_depth=3,
        random_state=42,
        verbose=-1
    )

    model.fit(X, y)

    return model



@pytest.fixture
def mock_vault_client(monkeypatch):
    """Mock du client Vault pour les tests"""
    class MockKV:
        class MockV2:
            def read_secret_version(self, path):
                return {
                    'data': {
                        'data': {
                            'POSTGRES_HOST': 'localhost',
                            'POSTGRES_PORT': '5432',
                            'POSTGRES_DB': 'test_db',
                            'POSTGRES_USER': 'test_user',
                            'POSTGRES_PASSWORD': 'test_password',
                            'URL': 'http://test-url.com',
                            'URL_ecb_eurozone_cpi': 'http://test-ecb.com',
                            'URL_pib': 'http://test-pib.com',
                        }
                    }
                }

        def __init__(self):
            self.v2 = self.MockV2()

    class MockSecrets:
        def __init__(self):
            self.kv = MockKV()

    class MockVaultClient:
        def __init__(self, *args, **kwargs):
            self.secrets = MockSecrets()

        def is_authenticated(self):
            return True

    import hvac
    monkeypatch.setattr(hvac, "Client", MockVaultClient)

    return MockVaultClient()



@pytest.fixture
def validation_thresholds():
    """Seuils de validation pour les tests de qualité"""
    return {
        'min_rows': 50,
        'max_null_ratio': 0.1,
        'min_close_value': 0.5,
        'max_close_value': 2.0,
        'min_volatility': 0.0,
        'max_volatility': 0.1,
    }



def assert_dataframe_valid(df, required_columns=None):
    """Helper pour valider un DataFrame"""
    assert df is not None, "DataFrame is None"
    assert len(df) > 0, "DataFrame is empty"

    if required_columns:
        missing = set(required_columns) - set(df.columns)
        assert not missing, f"Missing columns: {missing}"


def assert_no_leakage(df, time_col='time'):
    """Helper pour vérifier qu'il n'y a pas de leakage temporel"""
    assert df[time_col].is_monotonic_increasing, "Time not sorted"
    assert df[time_col].duplicated().sum() == 0, "Duplicate timestamps"
