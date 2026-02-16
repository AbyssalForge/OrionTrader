# 🧪 Tests OrionTrader

Guide complet pour exécuter les tests automatisés du projet.

## 📁 Structure

```
tests/
├── conftest.py              # Fixtures partagées
├── test_bronze_service.py   # Tests extraction données
├── test_silver_service.py   # Tests transformations
├── test_api_endpoints.py    # Tests API REST
├── test_ml_pipeline.py      # Tests ML
└── README.md               # Ce fichier
```

## 🚀 Installation

```bash
# Installer dépendances de test
pip install -r requirements-dev.txt
```

## ▶️ Exécuter les tests

### Tous les tests
```bash
pytest tests/
```

### Tests par catégorie (markers)
```bash
# Tests unitaires uniquement
pytest tests/ -m unit

# Tests d'intégration
pytest tests/ -m integration

# Tests ML
pytest tests/ -m ml

# Tests API
pytest tests/ -m api

# Tests Bronze/Silver/Gold
pytest tests/ -m bronze
pytest tests/ -m silver
pytest tests/ -m gold
```

### Avec couverture de code
```bash
pytest tests/ --cov=airflow --cov=fastapi --cov-report=html
# Ouvrir htmlcov/index.html dans le navigateur
```

### Tests en parallèle (plus rapide)
```bash
pytest tests/ -n auto
```

### Tests verbeux avec détails
```bash
pytest tests/ -v -s
```

### Arrêter au premier échec
```bash
pytest tests/ -x
```

### Exécuter seulement les tests qui ont échoué
```bash
pytest tests/ --lf
```

## 📊 Rapports

### Génération rapport HTML
```bash
pytest tests/ --html=report.html --self-contained-html
```

### Rapport JUnit (pour CI)
```bash
pytest tests/ --junitxml=junit.xml
```

### Rapport de couverture
```bash
pytest tests/ --cov --cov-report=term-missing
pytest tests/ --cov --cov-report=html
pytest tests/ --cov --cov-report=xml  # Pour Codecov
```

## 🎯 Objectifs de couverture

| Module | Objectif | Actuel |
|--------|----------|--------|
| Bronze Service | 80% | TBD |
| Silver Service | 85% | TBD |
| Gold Service | 75% | TBD |
| FastAPI Routes | 70% | TBD |
| ML Pipeline | 80% | TBD |

## 🏷️ Markers disponibles

- `unit` - Tests unitaires rapides (<1s)
- `integration` - Tests d'intégration (avec DB, API)
- `ml` - Tests spécifiques au Machine Learning
- `api` - Tests des endpoints FastAPI
- `slow` - Tests lents (>5s)
- `bronze` - Tests couche Bronze
- `silver` - Tests couche Silver
- `gold` - Tests couche Gold

## 🔧 Configuration

Configuration dans `pytest.ini`:
- Timeout par défaut: 300s
- Coverage automatique: airflow/ et fastapi/
- Rapport HTML dans htmlcov/
- Rapport XML pour CI

## 📝 Écrire de nouveaux tests

### Template de test unitaire
```python
import pytest

@pytest.mark.unit
@pytest.mark.bronze
def test_my_function(sample_mt5_data):
    """Test description"""
    result = my_function(sample_mt5_data)

    assert result is not None
    assert result['status'] == 'success'
```

### Template de test d'intégration
```python
import pytest

@pytest.mark.integration
@pytest.mark.slow
def test_full_pipeline(test_db_session):
    """Test description"""
    # Setup
    ...

    # Execute
    result = run_pipeline()

    # Verify
    assert result is not None
```

### Utiliser fixtures
```python
def test_with_data(sample_mt5_data, temp_parquet_file):
    """Utilise fixtures de conftest.py"""
    pass
```

## 🐛 Debugging

### Exécuter un test spécifique
```bash
pytest tests/test_bronze_service.py::test_extract_mt5_data_valid_range
```

### Mode debug avec breakpoints
```bash
pytest tests/ --pdb
```

### Voir print() dans les tests
```bash
pytest tests/ -s
```

## 🤖 CI/CD

Les tests sont exécutés automatiquement par GitHub Actions sur:
- Push sur `main`, `develop`, `bloc_e3_ia`
- Pull requests
- Tags `v*.*.*`

Workflow: `.github/workflows/ci-tests.yml`

## 📚 Ressources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
- [Markers documentation](https://docs.pytest.org/en/stable/how-to/mark.html)
