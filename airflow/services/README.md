# Services Module - Business Logic

Ce module contient toute la logique métier du pipeline ETL, séparée des tasks Airflow.

## Architecture

```
services/
├── __init__.py              # Exports des fonctions
├── bronze_service.py        # Bronze Layer: Extraction & Loading
├── silver_service.py        # Silver Layer: Feature Engineering
├── gold_service.py          # Gold Layer: ML Datasets (TODO)
└── validation_service.py    # Validation & Notification
```

## Principe de séparation

### ❌ Avant (monolithe)
```python
@task
def extract_and_load_mt5(**context):
    # 50+ lignes de logique métier directement dans la task
    ...
```

### ✅ Après (séparation)
```python
# DAG (orchestration uniquement)
@task
def extract_and_load_mt5(**context):
    start, end = _get_dates(context)
    return extract_mt5_data(start, end)  # Appel au service

# Service (logique métier)
def extract_mt5_data(start, end):
    # Toute la logique métier ici
    ...
```

## Bronze Service (`bronze_service.py`)

Fonctions pour l'extraction et le chargement des données brutes.

### Fonctions publiques:

#### `initialize_database()`
Crée toutes les tables dans la base de données.

**Returns:** `dict` avec status

**Exemple:**
```python
result = initialize_database()
# {'status': 'success'}
```

#### `extract_mt5_data(start, end)`
Extrait et charge les données MT5 dans `raw_mt5_eurusd_m15`.

**Args:**
- `start`: Date de début (datetime)
- `end`: Date de fin (datetime)

**Returns:** `dict` avec status, rows, pipeline_run_id

**Exemple:**
```python
result = extract_mt5_data(
    start=datetime(2024, 1, 1),
    end=datetime(2024, 1, 31)
)
# {'status': 'success', 'rows': 2976, 'pipeline_run_id': '2024-01-31T12:00:00'}
```

#### `extract_stooq_data()`
Extrait et charge les données Stooq (DXY, VIX, SPX, Gold) dans `raw_stooq_daily`.

**Returns:** `dict` avec status, rows, pipeline_run_id

#### `extract_eurostat_data()`
Extrait et charge les données Eurostat (PIB, CPI, événements) dans `raw_eurostat_macro` et `raw_economic_events`.

**Returns:** `dict` avec status, rows, pipeline_run_id

---

## Silver Service (`silver_service.py`)

Fonctions pour la transformation et le feature engineering.

### Fonctions publiques:

#### `transform_features(mt5_result, stooq_result, eurostat_result)`
Transforme les données Bronze en features Silver.

**Args:**
- `mt5_result`: Résultat de `extract_mt5_data()`
- `stooq_result`: Résultat de `extract_stooq_data()`
- `eurostat_result`: Résultat de `extract_eurostat_data()`

**Returns:** `dict` avec status, rows, pipeline_run_id

**Processus:**
1. Charge MT5 (base M15)
2. Merge Stooq (resample daily → M15)
3. Merge Eurostat (resample monthly → M15)
4. Feature engineering
5. Nettoyage
6. Insertion dans `features_eurusd_m15`

#### `apply_feature_engineering(df)`
Applique le feature engineering sur un DataFrame.

**Args:**
- `df`: DataFrame avec données brutes mergées

**Returns:** DataFrame avec features calculées

**Features générées:**
- MT5 (11): momentum, volatilité, candlestick patterns
- Stooq (10): DXY, VIX, SPX, Gold trends
- Eurostat (5): PIB, CPI, événements
- Composites (2): alignement macro/micro

#### `insert_features_to_db(df, session, pipeline_run_id)`
Insère les features dans la table Silver.

**Args:**
- `df`: DataFrame avec features
- `session`: SQLAlchemy session
- `pipeline_run_id`: ID du pipeline run

**Returns:** Nombre de lignes insérées

### Fonctions privées (helpers):

- `_load_mt5_data()`: Charge MT5 depuis DB
- `_merge_stooq_data()`: Merge Stooq avec resample
- `_merge_eurostat_data()`: Merge Eurostat avec resample
- `_add_mt5_features()`: Ajoute features MT5
- `_add_stooq_features()`: Ajoute features Stooq
- `_add_eurostat_features()`: Ajoute features Eurostat
- `_add_composite_features()`: Ajoute features composites

---

## Gold Service (`gold_service.py`)

Fonctions pour la création des datasets ML.

### Fonctions publiques:

#### `create_ml_dataset(features_result)`
Crée les datasets ML depuis les features.

**Args:**
- `features_result`: Résultat de `transform_features()`

**Returns:** `dict` avec status et message

**TODO:** À implémenter
- Classification: Labels Buy/Sell/Hold
- Regression: Future returns
- RL: State/Action/Reward

---

## Validation Service (`validation_service.py`)

Fonctions pour la validation et les notifications.

### Fonctions publiques:

#### `validate_data_quality(bronze_mt5, bronze_stooq, bronze_eurostat, silver)`
Valide la qualité des données du pipeline.

**Args:**
- `bronze_mt5`: Résultat Bronze MT5
- `bronze_stooq`: Résultat Bronze Stooq
- `bronze_eurostat`: Résultat Bronze Eurostat
- `silver`: Résultat Silver

**Returns:** `dict` avec status, message, errors, warnings

**Validations:**
- Statuts de chaque layer
- Nombre minimum de lignes (>100)
- Cohérence des données

#### `send_discord_notification(validation_result, webhook_url)`
Envoie une notification Discord.

**Args:**
- `validation_result`: Résultat de `validate_data_quality()`
- `webhook_url`: URL du webhook Discord

**Returns:** Status de l'envoi ("Notification sent" ou erreur)

---

## Utilisation dans un DAG

```python
from airflow.sdk import task
from services import (
    initialize_database,
    extract_mt5_data,
    transform_features,
    validate_data_quality,
    send_discord_notification
)

@task
def init_database():
    return initialize_database()

@task
def extract_and_load_mt5(**context):
    start, end = _get_dates(context)
    return extract_mt5_data(start, end)

@task
def transform_to_features(mt5_result, stooq_result, eurostat_result):
    return transform_features(mt5_result, stooq_result, eurostat_result)

@task
def validate_pipeline(bronze_mt5, bronze_stooq, bronze_eurostat, silver):
    return validate_data_quality(bronze_mt5, bronze_stooq, bronze_eurostat, silver)

@task
def notify(validation_result):
    return send_discord_notification(validation_result, WEBHOOK_URL)
```

---

## Avantages de cette architecture

### 1. Séparation des préoccupations
- **DAG**: Orchestration Airflow uniquement
- **Services**: Logique métier réutilisable

### 2. Testabilité
```python
# Tester la logique métier sans Airflow
def test_feature_engineering():
    df = pd.DataFrame(...)
    result = apply_feature_engineering(df)
    assert 'close_return' in result.columns
```

### 3. Réutilisabilité
```python
# Utiliser les services dans d'autres contextes
from services import extract_mt5_data

# Script standalone
data = extract_mt5_data(start, end)
```

### 4. Maintenabilité
- Code modulaire et organisé
- Fonctions avec responsabilité unique
- Documentation claire

### 5. Lisibilité
- DAG concis (165 lignes vs 600+)
- Logique métier bien structurée
- Helpers privés pour clarté

---

## Guidelines de développement

### Naming conventions
- Fonctions publiques: `verb_noun()` (ex: `extract_mt5_data()`)
- Fonctions privées: `_verb_noun()` (ex: `_load_mt5_data()`)
- Services: `noun_service.py` (ex: `bronze_service.py`)

### Return values
Toujours retourner un dict avec au minimum:
```python
{
    'status': 'success' | 'failed' | 'pending',
    'rows': int,  # si applicable
    'pipeline_run_id': str  # si applicable
}
```

### Error handling
```python
try:
    # Logique métier
    session.commit()
except Exception as e:
    session.rollback()
    print(f"[SERVICE] ❌ Erreur: {e}")
    raise  # Re-raise pour que Airflow gère le retry
finally:
    session.close()
```

### Logging
Utiliser des préfixes clairs:
- `[BRONZE/MT5]` pour Bronze MT5
- `[SILVER]` pour Silver
- `[GOLD]` pour Gold
- `[VALIDATE]` pour Validation
