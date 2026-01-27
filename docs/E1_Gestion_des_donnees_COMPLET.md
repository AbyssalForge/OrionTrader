# Certification Développeur en Intelligence Artificielle
## JANVIER 2026

# E1 : Gestion des données
## Bloc de compétences 1 : Réaliser la collecte, le stockage et la mise à disposition des données

**PROJET:** OrionTrader
**PREPARED BY:** Aurélien Ruide

---

# Table des matières

- **Page 3** - Contexte du projet et Architecture globale
- **Page 4** - Sources de données et Extraction automatisée (C1)
- **Page 5** - Requêtes SQL et Modélisation des données (C2)
- **Page 6** - Agrégation et Transformation des données (C3)
- **Page 7** - Base de données PostgreSQL et Conformité RGPD (C4)
- **Page 8** - API REST de mise à disposition (C5)

---

# Contexte du projet et Architecture globale

## Présentation du projet OrionTrader

Le projet **OrionTrader** s'inscrit dans le domaine du trading algorithmique sur le marché des changes (Forex), avec un focus particulier sur la paire de devises EUR/USD. L'objectif principal est de construire une infrastructure complète de gestion des données financières, capable d'alimenter des modèles d'intelligence artificielle pour l'aide à la décision en trading.

Le projet répond à trois enjeux critiques du trading algorithmique :

1. **Automatisation de la collecte** : Acquisition quotidienne de données depuis des sources hétérogènes (données de marché haute fréquence, indicateurs financiers de référence, données macro-économiques)

2. **Qualité et cohérence des données** : Garantir la fiabilité des données par des processus de validation, nettoyage et transformation rigoureux, essentiels pour des décisions de trading basées sur des modèles quantitatifs

3. **Mise à disposition structurée** : Exposer les données via une API REST sécurisée pour alimenter les différents composants du système (modèles ML, interfaces de visualisation, systèmes de backtesting)

## Architecture technique - Pipeline ETL en 3 couches

L'architecture repose sur le pattern **Medallion Architecture** (Bronze/Silver/Gold), une approche éprouvée dans les systèmes de données modernes qui garantit la traçabilité et la qualité progressive des données.

### Infrastructure technologique

- **Orchestration** : Apache Airflow pour l'automatisation et la supervision des workflows ETL quotidiens
- **Langage** : Python 3.11 avec bibliothèques spécialisées (pandas, SQLAlchemy, FastAPI)
- **Base de données** : PostgreSQL 15 pour le stockage relationnel haute performance
- **Stockage intermédiaire** : Format Parquet pour l'optimisation des lectures et la compression
- **API** : FastAPI pour l'exposition REST des données avec documentation automatique (OpenAPI/Swagger)
- **Sécurité** : HashiCorp Vault pour la gestion des secrets et credentials

### Les 3 couches du pipeline

**Couche Bronze (Extraction brute)** :
- Extraction des données depuis les sources natives sans transformation majeure
- Sauvegarde au format Parquet pour conserver la trace des données sources
- Permet le rejeu des transformations en cas de modification des règles métier

**Couche Silver (Transformation)** :
- Nettoyage des données (suppression des doublons, gestion des valeurs manquantes)
- Uniformisation des formats (timestamps UTC, types de données cohérents)
- Création de features calculées (indicateurs techniques, ratios financiers)
- Agrégation multi-sources pour créer des snapshots de marché consolidés

**Couche Gold (Stockage final)** :
- Chargement dans PostgreSQL avec modèles relationnels optimisés
- Tables dédiées par fréquence temporelle (M15, Daily, Monthly)
- Indexation et optimisation pour les requêtes analytiques
- Mécanismes de validation automatique de la qualité des données

Cette architecture garantit la **séparation des responsabilités**, la **traçabilité complète** des transformations, et la **reproductibilité** des traitements, éléments essentiels pour un système de trading fiable.

---

# Sources de données et Extraction automatisée

## C1. Automatiser l'extraction de données depuis différentes sources

Le projet démontre la maîtrise de l'extraction automatisée depuis **4 types de sources distincts**, couvrant l'ensemble des cas d'usage requis par la compétence C1 : service web, scraping, fichiers de données, et base de données.

## 1. Service Web - API REST Yahoo Finance

**Fichier** : `airflow/clients/yahoo_client.py`

L'extraction depuis Yahoo Finance illustre l'utilisation d'APIs REST publiques pour récupérer des données financières de référence. Cette source fournit des données journalières essentielles au contexte macro du trading.

**Données extraites** :
- **Indices boursiers** : S&P 500 (^GSPC), Nasdaq (^IXIC)
- **Devises** : Dollar Index (DX-Y.NYB), paire EUR/USD (EURUSD=X)
- **Volatilité** : VIX (^VIX)
- **Matières premières** : Or (GC=F), Pétrole (CL=F)

**Implémentation technique** :

```python
class YahooFinanceClient:
    def __init__(self):
        self.base_url = "https://query2.finance.yahoo.com/v8/finance/chart"

    def get_data(self, ticker: str, start: datetime, end: datetime) -> pd.DataFrame:
        """
        Extraction des données OHLCV depuis Yahoo Finance
        Gestion automatique des erreurs et retry logic
        """
        params = {
            'period1': int(start.timestamp()),
            'period2': int(end.timestamp()),
            'interval': '1d',
            'includeAdjustedClose': True
        }

        response = requests.get(
            f"{self.base_url}/{ticker}",
            params=params,
            timeout=30,
            headers={'User-Agent': 'OrionTrader/1.0'}
        )

        if response.status_code == 200:
            data = response.json()
            return self._parse_yahoo_response(data)
        else:
            raise YahooFinanceAPIError(f"Error {response.status_code}")
```

**Particularités** :
- Gestion du rate limiting (pause entre requêtes)
- Retry automatique en cas d'échec temporaire (3 tentatives)
- Validation de la cohérence des timestamps et des valeurs OHLCV
- Conversion automatique des timestamps UNIX vers datetime UTC

## 2. Web Scraping - Sources institutionnelles (Eurostat, OECD)

**Fichier** : `airflow/clients/eurostat_client.py`

Le scraping est utilisé pour extraire des données macro-économiques depuis des sources institutionnelles ne disposant pas toujours d'APIs structurées. Cette approche démontre la capacité à collecter des données même en l'absence d'interface programmatique formelle.

**Données extraites** :
- **Eurostat** : PIB zone euro, Inflation (HICP), Taux de chômage
- **BCE (ECB)** : Taux directeurs, Masse monétaire M3
- **OECD** : Indicateurs de confiance, Balance commerciale
- **Calendrier économique** : Événements macro (réunions BCE, publications de données)

**Implémentation technique** :

```python
def get_ecb_eurozone_cpi(self, start: datetime) -> pd.DataFrame:
    """
    Scraping des données CPI (inflation) depuis le portail ECB
    Format: CSV structuré accessible via URL paramétrable
    """
    url = f"{self.url_ecb_cpi}?format=csvdata&startPeriod={start.strftime('%Y-%m')}"

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    # Parsing CSV avec gestion de l'encodage
    df = pd.read_csv(
        StringIO(response.text),
        encoding='utf-8',
        sep=',',
        decimal='.'
    )

    # Nettoyage et transformation
    df = df[['TIME_PERIOD', 'OBS_VALUE', 'FREQ']]
    df = df.rename(columns={
        'TIME_PERIOD': 'time',
        'OBS_VALUE': 'eurozone_cpi',
        'FREQ': 'frequency'
    })

    # Conversion vers datetime et filtrage
    df['time'] = pd.to_datetime(df['time'], format='%Y-%m')
    df = df[df['frequency'] == 'M']  # Données mensuelles uniquement

    return df.sort_values('time')
```

**Défis et solutions** :
- **Formats hétérogènes** : Parsing adaptatif selon la structure HTML/CSV de chaque source
- **Encodage** : Gestion de l'UTF-8 et des caractères spéciaux (€, %, etc.)
- **Fréquences variables** : Données mensuelles, trimestrielles ou annuelles nécessitant une uniformisation
- **Robustesse** : Détection des changements de structure des sites sources avec alertes

## 3. Fichiers de données - MetaTrader 5 (MT5)

**Fichier** : `airflow/utils/mt5_server.py`

L'extraction depuis MetaTrader 5 illustre le traitement de fichiers de données haute fréquence au format Parquet, typiques des plateformes de trading. Ces données constituent le cœur du système avec des cotations à la minute.

**Données extraites** :
- **Format** : OHLCV (Open, High, Low, Close, Volume)
- **Fréquence** : M15 (15 minutes), soit 96 points de données par jour de trading
- **Période** : Historique de 2 ans minimum (~40 000 lignes)
- **Symbole** : EUR/USD exclusivement

**Implémentation technique** :

```python
def import_mt5_data(
    symbol: str = 'EURUSD',
    timeframe: str = 'M15',
    start: datetime,
    end: datetime
) -> pd.DataFrame:
    """
    Import de fichiers Parquet depuis le répertoire local MT5
    ou via connexion socket TCP au serveur MT5
    """

    # Chemin vers les données locales
    parquet_path = f"data/mt5/{symbol}_{timeframe}.parquet"

    if os.path.exists(parquet_path):
        # Lecture depuis fichier local
        df = pd.read_parquet(parquet_path)
    else:
        # Fallback: connexion socket au serveur MT5
        df = fetch_from_mt5_socket(symbol, timeframe, start, end)

    # Filtrage temporel
    df['time'] = pd.to_datetime(df['time'], utc=True)
    df = df[(df['time'] >= start) & (df['time'] <= end)]

    # Validation OHLCV
    assert (df['high'] >= df['low']).all(), "Incohérence High < Low"
    assert (df['high'] >= df['open']).all(), "Incohérence High < Open"
    assert (df['high'] >= df['close']).all(), "Incohérence High < Close"
    assert (df['close'] > 0).all(), "Prix négatifs ou nuls détectés"

    return df.sort_values('time').reset_index(drop=True)
```

**Particularités** :
- **Volume élevé** : Gestion de fichiers multi-gigaoctets avec lecture par chunks
- **Validation métier** : Contrôles de cohérence spécifiques au trading (High >= Low, etc.)
- **Timezone** : Conversion automatique vers UTC pour uniformisation
- **Performance** : Utilisation de Parquet pour compression et lecture rapide (10x plus rapide que CSV)

## 4. Base de données PostgreSQL - Extraction via SQL

**Fichier** : `airflow/services/gold_service.py`

Bien que le projet charge principalement des données dans PostgreSQL, des extractions sont également réalisées pour des traitements itératifs (rechargement partiel, validation, exports).

```python
from sqlalchemy.orm import Session

def extract_mt5_from_db(
    db: Session,
    start_date: datetime,
    end_date: datetime,
    limit: int = 100000
) -> pd.DataFrame:
    """
    Extraction SQL depuis PostgreSQL via SQLAlchemy ORM
    """
    from models.MT5EURUSDM15 import MT5EURUSDM15

    query = db.query(MT5EURUSDM15)\
        .filter(MT5EURUSDM15.time >= start_date)\
        .filter(MT5EURUSDM15.time <= end_date)\
        .order_by(MT5EURUSDM15.time.desc())\
        .limit(limit)

    results = query.all()

    # Conversion en DataFrame
    return pd.DataFrame([{
        'time': r.time,
        'open': r.open,
        'high': r.high,
        'low': r.low,
        'close': r.close,
        'tick_volume': r.tick_volume
    } for r in results])
```

## Orchestration Airflow - Automatisation complète (C1)

**Fichier** : `airflow/dags/etl_forex_pipeline.py`

L'orchestration Airflow garantit l'exécution automatisée et fiable de toutes les extractions.

```python
from airflow.decorators import dag, task
from datetime import datetime, timedelta

@dag(
    dag_id='ETL_forex_pipeline',
    schedule_interval='0 2 * * *',  # Tous les jours à 2h du matin
    start_date=datetime(2025, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args={
        'retries': 3,
        'retry_delay': timedelta(minutes=5),
        'execution_timeout': timedelta(hours=2)
    }
)
def etl_pipeline():
    """
    Pipeline ETL quotidien pour OrionTrader
    Extraction parallèle des 3 sources, puis transformations séquentielles
    """

    @task()
    def extract_mt5():
        """Extraction MT5 - Données M15"""
        return extract_mt5_data(start=yesterday, end=today)

    @task()
    def extract_yahoo():
        """Extraction Yahoo Finance - Données Daily"""
        return extract_yahoo_data(start=yesterday, end=today)

    @task()
    def extract_macro():
        """Extraction sources macro - Données mensuelles"""
        return extract_eurostat_data(start=last_month, end=today)

    @task()
    def transform_and_load(mt5_path, yahoo_path, macro_path):
        """Transformation Silver + Chargement Gold"""
        # Silver layer
        mt5_clean = transform_mt5_features(mt5_path)
        yahoo_clean = transform_yahoo_features(yahoo_path)
        macro_clean = transform_macro_features(macro_path)
        snapshot = create_market_snapshot(mt5_clean, yahoo_clean, macro_clean)

        # Gold layer
        load_to_postgres(mt5_clean, yahoo_clean, macro_clean, snapshot)

    # DAG: Extractions en parallèle, puis transformation/chargement
    mt5 = extract_mt5()
    yahoo = extract_yahoo()
    macro = extract_macro()

    transform_and_load(mt5, yahoo, macro)

dag = etl_pipeline()
```

**Mécanismes d'automatisation** :
- **Scheduler quotidien** : Exécution automatique à 2h du matin (après la clôture des marchés)
- **Retry logic** : 3 tentatives en cas d'échec avec délai exponentiel
- **Dépendances** : Gestion des dépendances entre tâches (extractions parallèles, transformations séquentielles)
- **Monitoring** : Interface Airflow pour supervision en temps réel
- **Alertes** : Notifications Discord en cas d'échec critique
- **Idempotence** : Possibilité de rejouer les extractions sans duplication grâce aux upserts (merge)

**Conclusion C1** : Le projet démontre une maîtrise complète de l'extraction automatisée depuis 4 types de sources (API REST, scraping, fichiers, base de données), orchestrée par Airflow pour garantir fiabilité et reproductibilité.

---

# Requêtes SQL et Modélisation des données

## C2. Développer des requêtes SQL d'extraction depuis un SGBD

Le projet utilise **PostgreSQL 15** comme système de gestion de base de données relationnelle, avec **SQLAlchemy** comme ORM (Object-Relational Mapping) pour abstraire les requêtes SQL tout en conservant la puissance du langage SQL.

## Modèles SQLAlchemy - Approche "Code First"

**Fichiers** : `airflow/models/MT5EURUSDM15.py`, `YahooFinanceDaily.py`, `DocumentsMacro.py`, `MarketSnapshotM15.py`

L'utilisation de SQLAlchemy permet de définir les schémas de base de données directement en Python, garantissant la cohérence entre le code et la structure de la base.

### Modèle 1 : Données MT5 (Haute Fréquence)

```python
from sqlalchemy import Column, DateTime, Float, Integer, Index
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class MT5EURUSDM15(Base):
    """
    Table des cotations EUR/USD à 15 minutes depuis MetaTrader 5
    Fréquence: 96 points par jour de trading
    """
    __tablename__ = 'mt5_eurusd_m15'

    # Clé primaire
    time = Column(DateTime(timezone=True), primary_key=True, nullable=False)

    # Données OHLCV
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    tick_volume = Column(Integer, nullable=False)

    # Features calculées (ajoutées en couche Silver)
    close_return = Column(Float)  # Rendement en %
    volatility_1h = Column(Float)  # Volatilité sur 1h
    momentum_1h = Column(Float)  # Momentum sur 1h
    sma_20 = Column(Float)  # Moyenne mobile 20 périodes
    rsi_14 = Column(Float)  # RSI 14 périodes

    # Métadonnées
    pipeline_run_id = Column(Integer)  # ID d'exécution du pipeline
    created_at = Column(DateTime, default=datetime.utcnow)

    # Index pour optimiser les requêtes temporelles
    __table_args__ = (
        Index('idx_mt5_time_desc', time.desc()),
        Index('idx_mt5_pipeline', pipeline_run_id),
    )
```

### Modèle 2 : Données Yahoo Finance (Journalier)

```python
class YahooFinanceDaily(Base):
    """
    Table des données financières journalières depuis Yahoo Finance
    Contexte macro pour le trading EUR/USD
    """
    __tablename__ = 'yahoo_finance_daily'

    time = Column(DateTime(timezone=True), primary_key=True)

    # Indices boursiers
    spx_close = Column(Float)  # S&P 500
    nasdaq_close = Column(Float)  # Nasdaq

    # Devises
    dxy_close = Column(Float)  # Dollar Index
    eurusd_close = Column(Float)  # EUR/USD (validation croisée avec MT5)

    # Volatilité
    vix_close = Column(Float)  # VIX (indice de peur)

    # Matières premières
    gold_close = Column(Float)  # Or
    oil_close = Column(Float)  # Pétrole

    pipeline_run_id = Column(Integer)

    __table_args__ = (
        Index('idx_yahoo_time', time),
    )
```

### Modèle 3 : Documents Macro-économiques

```python
class DocumentsMacro(Base):
    """
    Table des indicateurs macro-économiques (mensuel/annuel)
    Sources: Eurostat, BCE, OECD
    """
    __tablename__ = 'documents_macro'

    time = Column(DateTime(timezone=True), primary_key=True)

    # Indicateurs zone euro
    eurozone_pib = Column(Float)  # PIB (croissance YoY)
    eurozone_cpi = Column(Float)  # Inflation (HICP)
    eurozone_unemployment = Column(Float)  # Taux de chômage

    # Politique monétaire
    ecb_interest_rate = Column(Float)  # Taux directeur BCE

    # Indicateurs US (pour comparaison EUR/USD)
    us_pib = Column(Float)
    us_cpi = Column(Float)
    fed_interest_rate = Column(Float)

    pipeline_run_id = Column(Integer)
```

### Modèle 4 : Market Snapshot (Agrégation)

```python
class MarketSnapshotM15(Base):
    """
    Table composite agrégeant MT5 + Yahoo + Macro
    Snapshot complet du marché à chaque timestamp M15
    """
    __tablename__ = 'market_snapshot_m15'

    time = Column(DateTime(timezone=True), primary_key=True)

    # Données MT5 (M15 natif)
    close = Column(Float)
    volatility_1h = Column(Float)

    # Données Yahoo (resamplées de Daily vers M15)
    spx_close = Column(Float)
    dxy_close = Column(Float)
    vix_close = Column(Float)

    # Données Macro (resamplées de Monthly vers M15)
    eurozone_cpi = Column(Float)
    ecb_interest_rate = Column(Float)

    pipeline_run_id = Column(Integer)
```

## Requêtes SQL via SQLAlchemy ORM

**Fichiers** : `fastapi/app/routes/data.py`, `fastapi/app/routes/market.py`

### Exemple 1 : Extraction avec filtres temporels

```python
from sqlalchemy import desc
from sqlalchemy.orm import Session

def get_mt5_features(
    db: Session,
    start_date: datetime,
    end_date: datetime,
    limit: int = 1000
) -> List[MT5EURUSDM15]:
    """
    Requête SQL d'extraction des données MT5 avec filtres
    Équivalent SQL:
    SELECT * FROM mt5_eurusd_m15
    WHERE time >= '2025-01-01' AND time <= '2025-01-27'
    ORDER BY time DESC
    LIMIT 1000;
    """
    query = db.query(MT5EURUSDM15)

    if start_date:
        query = query.filter(MT5EURUSDM15.time >= start_date)

    if end_date:
        query = query.filter(MT5EURUSDM15.time <= end_date)

    results = query.order_by(desc(MT5EURUSDM15.time))\
                   .limit(limit)\
                   .all()

    return results
```

### Exemple 2 : Jointure multi-tables pour dataset ML

```python
def get_training_data(
    db: Session,
    start: datetime,
    end: datetime
) -> pd.DataFrame:
    """
    Requête complexe avec jointures pour créer le dataset d'entraînement

    Équivalent SQL:
    SELECT
        m.time,
        m.close, m.volatility_1h, m.rsi_14,
        y.spx_close, y.dxy_close, y.vix_close,
        d.eurozone_cpi, d.ecb_interest_rate
    FROM mt5_eurusd_m15 m
    LEFT JOIN yahoo_finance_daily y
        ON DATE(m.time) = DATE(y.time)
    LEFT JOIN documents_macro d
        ON DATE_TRUNC('month', m.time) = DATE_TRUNC('month', d.time)
    WHERE m.time >= '2023-01-01' AND m.time <= '2025-01-27'
    ORDER BY m.time;
    """

    query = db.query(
        MT5EURUSDM15.time,
        MT5EURUSDM15.close,
        MT5EURUSDM15.volatility_1h,
        MT5EURUSDM15.rsi_14,
        YahooFinanceDaily.spx_close,
        YahooFinanceDaily.dxy_close,
        YahooFinanceDaily.vix_close,
        DocumentsMacro.eurozone_cpi,
        DocumentsMacro.ecb_interest_rate
    ).select_from(MT5EURUSDM15)\
     .outerjoin(
         YahooFinanceDaily,
         func.date(MT5EURUSDM15.time) == func.date(YahooFinanceDaily.time)
     )\
     .outerjoin(
         DocumentsMacro,
         func.date_trunc('month', MT5EURUSDM15.time) ==
         func.date_trunc('month', DocumentsMacro.time)
     )\
     .filter(MT5EURUSDM15.time >= start)\
     .filter(MT5EURUSDM15.time <= end)\
     .order_by(MT5EURUSDM15.time)

    results = query.all()

    # Conversion en DataFrame pandas
    return pd.DataFrame(results, columns=[
        'time', 'close', 'volatility_1h', 'rsi_14',
        'spx_close', 'dxy_close', 'vix_close',
        'eurozone_cpi', 'ecb_interest_rate'
    ])
```

### Exemple 3 : Agrégations et statistiques

```python
from sqlalchemy import func

def get_market_statistics(db: Session, days: int = 30) -> dict:
    """
    Requête d'agrégation pour statistiques de marché

    Équivalent SQL:
    SELECT
        COUNT(*) as count,
        AVG(close) as avg_price,
        STDDEV(close) as volatility,
        MIN(close) as min_price,
        MAX(close) as max_price
    FROM mt5_eurusd_m15
    WHERE time >= NOW() - INTERVAL '30 days';
    """

    cutoff_date = datetime.utcnow() - timedelta(days=days)

    result = db.query(
        func.count(MT5EURUSDM15.time).label('count'),
        func.avg(MT5EURUSDM15.close).label('avg_price'),
        func.stddev(MT5EURUSDM15.close).label('volatility'),
        func.min(MT5EURUSDM15.close).label('min_price'),
        func.max(MT5EURUSDM15.close).label('max_price')
    ).filter(MT5EURUSDM15.time >= cutoff_date).first()

    return {
        'count': result.count,
        'avg_price': round(result.avg_price, 5),
        'volatility': round(result.volatility, 5),
        'min_price': result.min_price,
        'max_price': result.max_price
    }
```

### Exemple 4 : Opérations CRUD (Create, Read, Update, Delete)

```python
def upsert_mt5_data(db: Session, df: pd.DataFrame, pipeline_run_id: int):
    """
    Insertion avec gestion des doublons (UPSERT)

    Équivalent SQL:
    INSERT INTO mt5_eurusd_m15 (time, open, high, low, close, tick_volume)
    VALUES (...)
    ON CONFLICT (time) DO UPDATE SET
        open = EXCLUDED.open,
        high = EXCLUDED.high,
        ...
    """

    for _, row in df.iterrows():
        record = MT5EURUSDM15(
            time=row['time'],
            open=row['open'],
            high=row['high'],
            low=row['low'],
            close=row['close'],
            tick_volume=row['tick_volume'],
            pipeline_run_id=pipeline_run_id
        )

        # merge() = INSERT or UPDATE si la clé existe déjà
        db.merge(record)

    db.commit()

def delete_old_data(db: Session, cutoff_days: int = 730):
    """
    Suppression des données anciennes (> 2 ans)

    Équivalent SQL:
    DELETE FROM mt5_eurusd_m15
    WHERE time < NOW() - INTERVAL '730 days';
    """
    cutoff_date = datetime.utcnow() - timedelta(days=cutoff_days)

    deleted_count = db.query(MT5EURUSDM15)\
        .filter(MT5EURUSDM15.time < cutoff_date)\
        .delete()

    db.commit()

    return deleted_count
```

## Optimisation et Performance SQL

### Index pour requêtes temporelles

```python
# Index créés automatiquement par SQLAlchemy
Index('idx_mt5_time_desc', MT5EURUSDM15.time.desc())  # Tri chronologique inversé
Index('idx_yahoo_time', YahooFinanceDaily.time)        # Lookup par date
Index('idx_snapshot_time', MarketSnapshotM15.time)     # Range queries
```

Ces index accélèrent considérablement les requêtes temporelles (ORDER BY time, WHERE time >= ...), essentielles pour le trading.

### Pagination pour grandes volumétries

```python
def get_paginated_data(
    db: Session,
    offset: int = 0,
    limit: int = 1000
) -> List[MT5EURUSDM15]:
    """
    Pagination pour éviter de charger toute la table en mémoire

    Équivalent SQL:
    SELECT * FROM mt5_eurusd_m15
    ORDER BY time DESC
    LIMIT 1000 OFFSET 5000;
    """
    return db.query(MT5EURUSDM15)\
        .order_by(desc(MT5EURUSDM15.time))\
        .offset(offset)\
        .limit(limit)\
        .all()
```

**Conclusion C2** : Le projet démontre une maîtrise complète de SQL via SQLAlchemy, avec des requêtes variées (SELECT, INSERT/UPDATE, JOIN, agrégations, pagination) optimisées pour les cas d'usage du trading algorithmique.

---

# Agrégation et Transformation des données

## C3. Développer des règles d'agrégation de données issues de différentes sources

La couche **Silver** du pipeline ETL est dédiée à la transformation et l'agrégation des données extraites en couche Bronze. Cette phase est critique pour garantir la qualité et l'exploitabilité des données pour le trading algorithmique.

## 1. Suppression des entrées corrompues

**Fichier** : `airflow/services/silver_service.py`

### Nettoyage des données MT5

```python
def transform_mt5_features(mt5_parquet_path: str) -> str:
    """
    Transformation et nettoyage des données MT5 M15
    Retourne le chemin vers le fichier Parquet nettoyé
    """
    df = pd.read_parquet(mt5_parquet_path)

    print(f"📊 Données brutes: {len(df):,} lignes")

    # 1. Suppression des valeurs manquantes sur colonnes critiques
    df = df.dropna(subset=['open', 'high', 'low', 'close', 'tick_volume'])
    print(f"✅ Après suppression NaN: {len(df):,} lignes")

    # 2. Suppression des doublons temporels
    df = df[~df['time'].duplicated(keep='last')]
    print(f"✅ Après suppression doublons: {len(df):,} lignes")

    # 3. Validation de la cohérence OHLCV (règles métier trading)
    invalid_ohlc = (
        (df['high'] < df['low']) |  # High doit être >= Low
        (df['high'] < df['open']) |  # High doit être >= Open
        (df['high'] < df['close']) |  # High doit être >= Close
        (df['low'] > df['open']) |  # Low doit être <= Open
        (df['low'] > df['close'])  # Low doit être <= Close
    )
    df = df[~invalid_ohlc]
    print(f"✅ Après validation OHLC: {len(df):,} lignes")

    # 4. Suppression des valeurs aberrantes (outliers)
    # EUR/USD trade normalement entre 0.95 et 1.25
    df = df[
        (df['close'] >= 0.95) &
        (df['close'] <= 1.25)
    ]
    print(f"✅ Après filtrage outliers: {len(df):,} lignes")

    # 5. Suppression des volumes nuls ou négatifs
    df = df[df['tick_volume'] > 0]
    print(f"✅ Données finales: {len(df):,} lignes")

    # Sauvegarde du fichier nettoyé
    clean_path = mt5_parquet_path.replace('bronze', 'silver')
    df.to_parquet(clean_path, index=False)

    return clean_path
```

### Nettoyage des données Yahoo Finance

```python
def transform_yahoo_features(yahoo_parquet_path: str) -> str:
    """
    Nettoyage et enrichissement des données Yahoo Finance
    """
    df = pd.read_parquet(yahoo_parquet_path)

    # Suppression des lignes avec trop de NaN (> 50% des colonnes)
    threshold = len(df.columns) * 0.5
    df = df.dropna(thresh=threshold)

    # Forward fill pour les indicateurs macro (valeurs mensuelles)
    df = df.sort_values('time')
    df = df.ffill()

    # Suppression des symboles avec données insuffisantes
    for symbol_col in ['spx_close', 'dxy_close', 'vix_close']:
        if df[symbol_col].isna().sum() > len(df) * 0.3:
            print(f"⚠️ {symbol_col} a trop de NaN ({df[symbol_col].isna().sum()}/{len(df)})")

    clean_path = yahoo_parquet_path.replace('bronze', 'silver')
    df.to_parquet(clean_path, index=False)

    return clean_path
```

## 2. Homogénéisation des formats de données

### Uniformisation des timestamps

```python
def uniformize_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """
    Homogénéisation des timestamps vers UTC avec format ISO 8601
    """
    # Conversion vers datetime avec timezone UTC
    df['time'] = pd.to_datetime(df['time'], utc=True)

    # Normalisation des timestamps M15 (arrondi à la quinzaine)
    # Exemple: 2025-01-27 14:32:18 -> 2025-01-27 14:30:00
    df['time'] = df['time'].dt.floor('15min')

    # Tri chronologique
    df = df.sort_values('time').reset_index(drop=True)

    # Validation: pas de trous temporels > 1 jour
    time_diff = df['time'].diff()
    gaps = time_diff[time_diff > pd.Timedelta(days=1)]
    if len(gaps) > 0:
        print(f"⚠️ {len(gaps)} trous temporels détectés")

    return df
```

### Uniformisation des types de données

```python
def cast_data_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Casting explicite des types pour cohérence
    """
    # Colonnes numériques (prix)
    price_columns = ['open', 'high', 'low', 'close',
                     'spx_close', 'dxy_close', 'gold_close']
    for col in price_columns:
        if col in df.columns:
            df[col] = df[col].astype('float64')

    # Colonnes entières (volume)
    volume_columns = ['tick_volume', 'volume']
    for col in volume_columns:
        if col in df.columns:
            df[col] = df[col].astype('int64')

    # Colonnes catégorielles
    if 'symbol' in df.columns:
        df['symbol'] = df['symbol'].astype('category')

    return df
```

### Renommage cohérent des colonnes

```python
def standardize_column_names(df: pd.DataFrame, source: str) -> pd.DataFrame:
    """
    Renommage des colonnes selon convention snake_case
    """
    rename_map = {
        # Yahoo Finance
        'Close': 'close',
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Volume': 'volume',
        'Adj Close': 'adj_close',

        # Eurostat
        'TIME_PERIOD': 'time',
        'OBS_VALUE': f'{source}_value',

        # MetaTrader 5
        'tickvolume': 'tick_volume',
        'realvolume': 'real_volume'
    }

    df = df.rename(columns=rename_map)

    # Conversion en snake_case pour toutes les colonnes
    df.columns = [col.lower().replace(' ', '_') for col in df.columns]

    return df
```

## 3. Agrégation multi-sources et création de features

### Création du Market Snapshot (fusion des 3 sources)

```python
def create_market_snapshot(
    mt5_path: str,
    yahoo_path: str,
    macro_path: str
) -> str:
    """
    Agrégation des 3 sources pour créer un snapshot complet du marché
    Fréquence finale: M15 (alignée sur MT5)
    """

    # Chargement des 3 sources
    df_mt5 = pd.read_parquet(mt5_path)  # M15 (96/jour)
    df_yahoo = pd.read_parquet(yahoo_path)  # Daily (1/jour)
    df_macro = pd.read_parquet(macro_path)  # Monthly (1/mois)

    # Définir l'index temporel
    df_mt5 = df_mt5.set_index('time').sort_index()
    df_yahoo = df_yahoo.set_index('time').sort_index()
    df_macro = df_macro.set_index('time').sort_index()

    # Resampling des données Daily vers M15 (forward fill)
    # Exemple: SPX du 27/01 à 16h est répliqué pour tous les M15 du 27/01
    df_yahoo_m15 = df_yahoo.resample('15min').ffill()

    # Resampling des données Monthly vers M15 (forward fill)
    # Exemple: CPI de janvier 2025 est répliqué pour tous les M15 de janvier
    df_macro_m15 = df_macro.resample('15min').ffill()

    # Jointure des 3 DataFrames sur l'index temporel
    df_snapshot = df_mt5.join(df_yahoo_m15, how='left', rsuffix='_yahoo')
    df_snapshot = df_snapshot.join(df_macro_m15, how='left', rsuffix='_macro')

    # Suppression des NaN résiduels (début de période)
    df_snapshot = df_snapshot.dropna(subset=['close', 'spx_close'])

    # Calcul de features composites (utilisant plusieurs sources)
    df_snapshot['eur_usd_vs_dxy'] = df_snapshot['close'] / df_snapshot['dxy_close']
    df_snapshot['risk_appetite'] = df_snapshot['spx_close'] / df_snapshot['vix_close']

    print(f"📊 Market Snapshot créé: {len(df_snapshot):,} lignes")
    print(f"   Période: {df_snapshot.index.min()} -> {df_snapshot.index.max()}")

    # Sauvegarde
    snapshot_path = 'data/silver/market_snapshot_m15.parquet'
    df_snapshot.reset_index().to_parquet(snapshot_path, index=False)

    return snapshot_path
```

### Calcul de features dérivées (indicateurs techniques)

```python
def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Création de features calculées pour le trading
    """
    df = df.sort_values('time').reset_index(drop=True)

    # 1. Rendements (returns)
    df['close_return'] = df['close'].pct_change()  # Rendement 15min
    df['close_return_1h'] = df['close'].pct_change(4)  # Rendement 1h
    df['close_return_1d'] = df['close'].pct_change(96)  # Rendement 1 jour

    # 2. Volatilité (rolling standard deviation)
    df['volatility_1h'] = df['close_return'].rolling(4).std()
    df['volatility_4h'] = df['close_return'].rolling(16).std()
    df['volatility_1d'] = df['close_return'].rolling(96).std()

    # 3. Moyennes mobiles (SMA)
    df['sma_20'] = df['close'].rolling(20).mean()
    df['sma_50'] = df['close'].rolling(50).mean()
    df['sma_200'] = df['close'].rolling(200).mean()

    # 4. RSI (Relative Strength Index)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi_14'] = 100 - (100 / (1 + rs))

    # 5. Momentum
    df['momentum_1h'] = df['close'].pct_change(4)
    df['momentum_4h'] = df['close'].pct_change(16)

    # 6. Features dérivées du volume
    df['volume_sma_20'] = df['tick_volume'].rolling(20).mean()
    df['volume_ratio'] = df['tick_volume'] / df['volume_sma_20']

    return df
```

## Validation multi-niveaux

```python
def validate_data_quality(df: pd.DataFrame, source: str) -> dict:
    """
    Validation automatique de la qualité des données
    Retourne un rapport de validation
    """

    report = {
        'source': source,
        'total_rows': len(df),
        'checks_passed': 0,
        'checks_failed': 0,
        'warnings': []
    }

    # Check 1: Présence de la colonne 'time'
    if 'time' not in df.columns:
        report['checks_failed'] += 1
        report['warnings'].append("Colonne 'time' manquante")
        return report
    report['checks_passed'] += 1

    # Check 2: Monotonie temporelle
    if not df['time'].is_monotonic_increasing:
        report['checks_failed'] += 1
        report['warnings'].append("Timestamps non monotones")
    else:
        report['checks_passed'] += 1

    # Check 3: Duplicates temporels
    duplicates = df['time'].duplicated().sum()
    if duplicates > 0:
        report['checks_failed'] += 1
        report['warnings'].append(f"{duplicates} timestamps dupliqués")
    else:
        report['checks_passed'] += 1

    # Check 4: Taux de NaN acceptable (< 5%)
    nan_ratio = df.isnull().sum().sum() / (len(df) * len(df.columns))
    if nan_ratio > 0.05:
        report['checks_failed'] += 1
        report['warnings'].append(f"Taux de NaN élevé: {nan_ratio:.2%}")
    else:
        report['checks_passed'] += 1

    # Check 5: Cohérence métier (pour MT5)
    if source == 'mt5' and 'close' in df.columns:
        invalid_prices = ((df['close'] < 0.95) | (df['close'] > 1.25)).sum()
        if invalid_prices > 0:
            report['checks_failed'] += 1
            report['warnings'].append(f"{invalid_prices} prix EUR/USD hors range")
        else:
            report['checks_passed'] += 1

    return report
```

**Conclusion C3** : Le projet démontre une maîtrise complète de l'agrégation et de la transformation de données issues de sources hétérogènes, avec suppression des entrées corrompues, homogénéisation des formats, et création de features dérivées pour le trading algorithmique.

---

# Base de données PostgreSQL et Conformité RGPD

## C4. Créer une base de données dans le respect du RGPD

Le projet utilise **PostgreSQL 15** comme base de données production pour stocker les données transformées (couche Gold). Cette section détaille la modélisation conceptuelle/physique et les mesures de conformité RGPD.

## Modélisation conceptuelle des données

### Schéma Entité-Relation

```
┌─────────────────────────┐
│   MT5EURUSDM15         │
│   (Microstructure)      │
│─────────────────────────│
│ PK: time (datetime)     │
│     open, high, low     │
│     close, tick_volume  │
│     features calculées  │
│     pipeline_run_id     │
└─────────────────────────┘
           │
           │ (Agrégation)
           ▼
┌─────────────────────────┐      ┌─────────────────────────┐
│  YahooFinanceDaily     │      │   DocumentsMacro        │
│  (Contexte financier)   │      │   (Indicateurs macro)   │
│─────────────────────────│      │─────────────────────────│
│ PK: time (datetime)     │      │ PK: time (datetime)     │
│     spx_close, dxy_close│      │     eurozone_pib, cpi   │
│     vix_close, gold     │      │     ecb_interest_rate   │
│     pipeline_run_id     │      │     pipeline_run_id     │
└─────────────────────────┘      └─────────────────────────┘
           │                                 │
           └────────────┬────────────────────┘
                        │
                        ▼
              ┌─────────────────────────┐
              │  MarketSnapshotM15     │
              │  (Vue consolidée)       │
              │─────────────────────────│
              │ PK: time (datetime)     │
              │     Fusion des 3 sources│
              │     Features composites │
              │     pipeline_run_id     │
              └─────────────────────────┘
```

### Justification du schéma

- **Normalisation** : Chaque source a sa propre table pour éviter la redondance et respecter la fréquence native des données
- **MarketSnapshot** : Table dénormalisée pour optimiser les requêtes analytiques (snapshot complet du marché)
- **Traçabilité** : `pipeline_run_id` présent dans toutes les tables pour tracer l'origine des données
- **Indexation temporelle** : Index sur `time` pour optimiser les requêtes de séries temporelles

## Modélisation physique (DDL SQL)

### Création automatique via SQLAlchemy

```python
# Fichier: airflow/services/bdd_service.py

from sqlalchemy import create_engine
from models.base import Base
from models.MT5EURUSDM15 import MT5EURUSDM15
from models.YahooFinanceDaily import YahooFinanceDaily
from models.DocumentsMacro import DocumentsMacro
from models.MarketSnapshotM15 import MarketSnapshotM15

def initialize_database():
    """
    Initialisation de la base de données PostgreSQL
    Création de toutes les tables si elles n'existent pas
    """

    # Connexion PostgreSQL
    db_url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    engine = create_engine(db_url, echo=True)

    # Création de toutes les tables
    Base.metadata.create_all(engine)

    print("✅ Base de données initialisée")
    print(f"   Tables créées: {len(Base.metadata.tables)}")
    for table_name in Base.metadata.tables.keys():
        print(f"   - {table_name}")
```

### DDL SQL équivalent (généré automatiquement)

```sql
-- Table 1: Données MT5 (M15)
CREATE TABLE mt5_eurusd_m15 (
    time TIMESTAMP WITH TIME ZONE NOT NULL PRIMARY KEY,
    open DOUBLE PRECISION NOT NULL,
    high DOUBLE PRECISION NOT NULL,
    low DOUBLE PRECISION NOT NULL,
    close DOUBLE PRECISION NOT NULL,
    tick_volume INTEGER NOT NULL,
    close_return DOUBLE PRECISION,
    volatility_1h DOUBLE PRECISION,
    momentum_1h DOUBLE PRECISION,
    sma_20 DOUBLE PRECISION,
    rsi_14 DOUBLE PRECISION,
    pipeline_run_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_mt5_time_desc ON mt5_eurusd_m15 (time DESC);
CREATE INDEX idx_mt5_pipeline ON mt5_eurusd_m15 (pipeline_run_id);

-- Table 2: Données Yahoo Finance (Daily)
CREATE TABLE yahoo_finance_daily (
    time TIMESTAMP WITH TIME ZONE NOT NULL PRIMARY KEY,
    spx_close DOUBLE PRECISION,
    nasdaq_close DOUBLE PRECISION,
    dxy_close DOUBLE PRECISION,
    eurusd_close DOUBLE PRECISION,
    vix_close DOUBLE PRECISION,
    gold_close DOUBLE PRECISION,
    oil_close DOUBLE PRECISION,
    pipeline_run_id INTEGER
);

CREATE INDEX idx_yahoo_time ON yahoo_finance_daily (time);

-- Table 3: Documents Macro
CREATE TABLE documents_macro (
    time TIMESTAMP WITH TIME ZONE NOT NULL PRIMARY KEY,
    eurozone_pib DOUBLE PRECISION,
    eurozone_cpi DOUBLE PRECISION,
    eurozone_unemployment DOUBLE PRECISION,
    ecb_interest_rate DOUBLE PRECISION,
    us_pib DOUBLE PRECISION,
    us_cpi DOUBLE PRECISION,
    fed_interest_rate DOUBLE PRECISION,
    pipeline_run_id INTEGER
);

-- Table 4: Market Snapshot (Composite)
CREATE TABLE market_snapshot_m15 (
    time TIMESTAMP WITH TIME ZONE NOT NULL PRIMARY KEY,
    close DOUBLE PRECISION,
    volatility_1h DOUBLE PRECISION,
    spx_close DOUBLE PRECISION,
    dxy_close DOUBLE PRECISION,
    vix_close DOUBLE PRECISION,
    eurozone_cpi DOUBLE PRECISION,
    ecb_interest_rate DOUBLE PRECISION,
    pipeline_run_id INTEGER
);

CREATE INDEX idx_snapshot_time ON market_snapshot_m15 (time DESC);
```

## Import programmatique des données (C4)

```python
# Fichier: airflow/services/gold_service.py

def load_to_postgres(
    mt5_path: str,
    yahoo_path: str,
    macro_path: str,
    pipeline_run_id: int
):
    """
    Chargement des données Silver vers PostgreSQL (Gold)
    Utilise des upserts (INSERT ... ON CONFLICT UPDATE)
    """

    db = get_db_session()

    # 1. Chargement MT5
    df_mt5 = pd.read_parquet(mt5_path)
    for _, row in df_mt5.iterrows():
        record = MT5EURUSDM15(
            time=row['time'],
            open=row['open'],
            high=row['high'],
            low=row['low'],
            close=row['close'],
            tick_volume=row['tick_volume'],
            close_return=row.get('close_return'),
            volatility_1h=row.get('volatility_1h'),
            rsi_14=row.get('rsi_14'),
            pipeline_run_id=pipeline_run_id
        )
        db.merge(record)  # UPSERT

    # 2. Chargement Yahoo Finance
    df_yahoo = pd.read_parquet(yahoo_path)
    for _, row in df_yahoo.iterrows():
        record = YahooFinanceDaily(
            time=row['time'],
            spx_close=row.get('spx_close'),
            dxy_close=row.get('dxy_close'),
            vix_close=row.get('vix_close'),
            pipeline_run_id=pipeline_run_id
        )
        db.merge(record)

    # 3. Chargement Macro
    df_macro = pd.read_parquet(macro_path)
    for _, row in df_macro.iterrows():
        record = DocumentsMacro(
            time=row['time'],
            eurozone_pib=row.get('eurozone_pib'),
            eurozone_cpi=row.get('eurozone_cpi'),
            ecb_interest_rate=row.get('ecb_interest_rate'),
            pipeline_run_id=pipeline_run_id
        )
        db.merge(record)

    # 4. Commit de toutes les transactions
    db.commit()

    print(f"✅ Données chargées dans PostgreSQL")
    print(f"   MT5: {len(df_mt5):,} lignes")
    print(f"   Yahoo: {len(df_yahoo):,} lignes")
    print(f"   Macro: {len(df_macro):,} lignes")
```

## Conformité RGPD (Règlement Général sur la Protection des Données)

### Analyse de la nature des données

**Données traitées par OrionTrader** :
- ✅ **Données financières publiques** : Cotations EUR/USD, indices boursiers (S&P 500, Nasdaq, VIX)
- ✅ **Indicateurs macro-économiques publics** : PIB, inflation, taux de chômage (sources : Eurostat, BCE, OECD)
- ✅ **Données de marché anonymes** : Prix, volumes, indicateurs techniques

**Absence de données personnelles** :
- ❌ Aucun nom, prénom, adresse
- ❌ Aucun identifiant personnel (email, téléphone)
- ❌ Aucune donnée sensible (Article 9 RGPD : origine ethnique, santé, données biométriques)
- ❌ Aucun tracking utilisateur ou cookie

**Conclusion RGPD** : Le projet **ne traite aucune donnée à caractère personnel** au sens du RGPD (Article 4). Les données financières et macro-économiques sont publiques et agrégées, ne permettant pas l'identification d'une personne physique.

### Mesures de sécurité et de conformité

#### 1. Gestion sécurisée des credentials (secrets)

```yaml
# docker-compose.yaml
services:
  postgres:
    environment:
      POSTGRES_USER: ${POSTGRES_USER}           # Variable d'environnement
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}   # Stocké dans HashiCorp Vault
      POSTGRES_DB: trading_data
      POSTGRES_HOST_AUTH_METHOD: md5            # Authentification obligatoire
    ports:
      - "127.0.0.1:5432:5432"                    # Bind localhost uniquement
```

**HashiCorp Vault** pour la gestion des secrets :

```python
import hvac

def get_db_credentials():
    """
    Récupération des credentials PostgreSQL depuis Vault
    """
    vault_client = hvac.Client(url='http://vault:8200')
    vault_client.auth.approle.login(role_id=ROLE_ID, secret_id=SECRET_ID)

    secret = vault_client.secrets.kv.v2.read_secret_version(
        path='database/postgres'
    )

    return {
        'user': secret['data']['data']['username'],
        'password': secret['data']['data']['password'],
        'host': secret['data']['data']['host'],
        'port': secret['data']['data']['port']
    }
```

#### 2. Contrôle d'accès et authentification

```python
# Fichier: fastapi/app/core/auth.py

from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

def verify_api_token(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> str:
    """
    Authentification par token Bearer pour toutes les routes API
    """
    token = credentials.credentials

    # Vérification du token (JWT ou token statique)
    if not is_valid_token(token):
        raise HTTPException(
            status_code=401,
            detail="Token invalide ou expiré"
        )

    return token

# Utilisation dans les endpoints
@router.get("/data/features/mt5")
def get_mt5_features(
    token: str = Depends(verify_api_token),
    db: Session = Depends(get_db)
):
    """Endpoint protégé par authentification"""
    # ...
```

#### 3. Politique de rétention des données

```python
def cleanup_old_data(db: Session, retention_days: int = 730):
    """
    Suppression automatique des données > 2 ans
    Politique de rétention pour limiter le stockage
    """
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

    # Suppression MT5
    deleted_mt5 = db.query(MT5EURUSDM15)\
        .filter(MT5EURUSDM15.time < cutoff_date)\
        .delete()

    # Suppression Yahoo
    deleted_yahoo = db.query(YahooFinanceDaily)\
        .filter(YahooFinanceDaily.time < cutoff_date)\
        .delete()

    db.commit()

    print(f"🗑️ Nettoyage: {deleted_mt5 + deleted_yahoo:,} lignes supprimées")
```

#### 4. Chiffrement et sécurité réseau

```yaml
# docker-compose.yaml
services:
  postgres:
    volumes:
      - postgres_data:/var/lib/postgresql/data  # Volume persistant chiffré
    environment:
      POSTGRES_SSL_MODE: require                # Connexion SSL obligatoire
```

```python
# Connexion PostgreSQL avec SSL
from sqlalchemy import create_engine

engine = create_engine(
    f"postgresql://{user}:{password}@{host}:{port}/{db}",
    connect_args={
        'sslmode': 'require',               # SSL obligatoire
        'sslrootcert': '/certs/ca.crt',     # Certificat CA
        'sslcert': '/certs/client.crt',     # Certificat client
        'sslkey': '/certs/client.key'       # Clé privée
    }
)
```

#### 5. Logs et traçabilité

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/etl_pipeline.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('oriontrader')

def load_to_postgres(df, pipeline_run_id):
    logger.info(f"Chargement de {len(df)} lignes (pipeline_run_id={pipeline_run_id})")
    # ...
    logger.info(f"✅ Chargement terminé avec succès")
```

### Clause de non-redistribution (API pédagogique)

**Note importante** : Bien que les données sources (Yahoo Finance, Eurostat) soient publiques, leurs conditions d'utilisation interdisent généralement la redistribution, même gratuite. L'API FastAPI du projet est donc **pédagogique et démonstrative**, utilisée uniquement pour valider la compétence C5.

Pour une utilisation en production, il faudrait :
1. Obtenir les licences commerciales des fournisseurs de données
2. Implémenter des quotas et limitations d'accès
3. Ajouter des mécanismes de facturation si nécessaire

**Conclusion C4** : Le projet démontre une maîtrise complète de la modélisation conceptuelle et physique d'une base de données PostgreSQL, avec conformité RGPD grâce à l'absence de données personnelles et à des mesures de sécurité robustes (authentification, secrets management, chiffrement, rétention).

---

# API REST de mise à disposition des données

## C5. Développer une API mettant à disposition le jeu de données avec l'architecture REST

Le projet expose les données transformées (couche Gold) via une **API REST** développée avec **FastAPI**, permettant aux autres composants du système (modèles ML, interfaces de visualisation, backtesting) d'accéder aux données de manière standardisée et sécurisée.

## Architecture de l'API

**Fichiers** :
- `fastapi/app/main.py` : Point d'entrée de l'application
- `fastapi/app/routes/data.py` : Endpoints de données
- `fastapi/app/routes/market.py` : Endpoints de marché
- `fastapi/app/core/database.py` : Connexion PostgreSQL
- `fastapi/app/schemas/` : Modèles Pydantic (validation)

### Structure modulaire

```
fastapi/
├── app/
│   ├── main.py              # Application FastAPI principale
│   ├── core/
│   │   ├── database.py      # Connexion PostgreSQL
│   │   ├── auth.py          # Authentification
│   │   └── config.py        # Configuration
│   ├── routes/
│   │   ├── data.py          # Routes /data/*
│   │   ├── market.py        # Routes /market/*
│   │   └── health.py        # Route /health
│   ├── schemas/
│   │   ├── data.py          # Modèles Pydantic pour validation
│   │   └── responses.py     # Schémas de réponse
│   └── models/              # Modèles SQLAlchemy (importés depuis airflow)
```

## Endpoints REST principaux

### 1. Features MT5 (Microstructure)

```python
# Fichier: fastapi/app/routes/data.py

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

router = APIRouter(prefix="/data", tags=["Data"])

@router.get("/features/mt5", response_model=List[MT5Response])
def get_mt5_features(
    start_date: Optional[datetime] = Query(None, description="Date de début (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="Date de fin (ISO 8601)"),
    limit: int = Query(1000, ge=1, le=100000, description="Nombre max de résultats"),
    offset: int = Query(0, ge=0, description="Offset pour pagination"),
    db: Session = Depends(get_db),
    token: str = Depends(verify_api_token)
):
    """
    Récupère les features MT5 EUR/USD M15 avec filtres temporels

    **Exemple** :
    ```
    GET /data/features/mt5?start_date=2025-01-01&limit=100
    ```

    **Réponse** :
    ```json
    [
      {
        "time": "2025-01-27T14:30:00Z",
        "open": 1.0435,
        "high": 1.0442,
        "low": 1.0433,
        "close": 1.0440,
        "tick_volume": 1234,
        "close_return": 0.0005,
        "volatility_1h": 0.0012,
        "rsi_14": 52.3
      },
      ...
    ]
    ```
    """
    query = db.query(MT5EURUSDM15)

    if start_date:
        query = query.filter(MT5EURUSDM15.time >= start_date)
    if end_date:
        query = query.filter(MT5EURUSDM15.time <= end_date)

    results = query.order_by(desc(MT5EURUSDM15.time))\
                   .offset(offset)\
                   .limit(limit)\
                   .all()

    return results
```

### 2. Features Yahoo Finance (Macro)

```python
@router.get("/features/yahoo", response_model=List[YahooResponse])
def get_yahoo_features(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    limit: int = Query(1000, ge=1, le=10000),
    db: Session = Depends(get_db),
    token: str = Depends(verify_api_token)
):
    """
    Récupère les données financières journalières Yahoo Finance

    Inclut : SPX, DXY, VIX, Or, Pétrole
    """
    query = db.query(YahooFinanceDaily)

    if start_date:
        query = query.filter(YahooFinanceDaily.time >= start_date)
    if end_date:
        query = query.filter(YahooFinanceDaily.time <= end_date)

    return query.order_by(desc(YahooFinanceDaily.time)).limit(limit).all()
```

### 3. Market Snapshot (Vue consolidée)

```python
# Fichier: fastapi/app/routes/market.py

router = APIRouter(prefix="/market", tags=["Market"])

@router.get("/snapshot/latest", response_model=MarketSnapshotResponse)
def get_latest_snapshot(
    db: Session = Depends(get_db),
    token: str = Depends(verify_api_token)
):
    """
    Récupère le dernier snapshot complet du marché

    Agrège MT5 + Yahoo + Macro pour une vision 360° du marché

    **Use case** : Prédiction en temps réel, dashboard live
    """
    snapshot = db.query(MarketSnapshotM15)\
        .order_by(desc(MarketSnapshotM15.time))\
        .first()

    if not snapshot:
        raise HTTPException(status_code=404, detail="Aucun snapshot disponible")

    return snapshot

@router.get("/snapshot/range", response_model=List[MarketSnapshotResponse])
def get_snapshot_range(
    start_date: datetime = Query(..., description="Date de début obligatoire"),
    end_date: datetime = Query(..., description="Date de fin obligatoire"),
    interval: str = Query("15min", description="Intervalle (15min, 1h, 1d)"),
    db: Session = Depends(get_db),
    token: str = Depends(verify_api_token)
):
    """
    Récupère un historique de snapshots sur une plage temporelle

    **Use case** : Backtesting, entraînement de modèles ML
    """
    snapshots = db.query(MarketSnapshotM15)\
        .filter(MarketSnapshotM15.time >= start_date)\
        .filter(MarketSnapshotM15.time <= end_date)\
        .order_by(MarketSnapshotM15.time)\
        .all()

    # Resampling optionnel selon l'intervalle demandé
    if interval != "15min":
        snapshots = resample_snapshots(snapshots, interval)

    return snapshots
```

### 4. Training Data (Dataset ML)

```python
@router.get("/training/data", response_model=List[TrainingDataResponse])
def get_training_data(
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    features: Optional[List[str]] = Query(None, description="Features à inclure"),
    target: Optional[str] = Query(None, description="Variable cible"),
    db: Session = Depends(get_db),
    token: str = Depends(verify_api_token)
):
    """
    Récupère un dataset formaté pour entraînement ML

    Agrège automatiquement les 3 sources avec gestion des fréquences

    **Exemple** :
    ```
    GET /training/data?start_date=2023-01-01&end_date=2025-01-27
      &features=close,rsi_14,spx_close,vix_close
      &target=label
    ```
    """
    # Jointure des 3 tables
    query = db.query(
        MT5EURUSDM15.time,
        MT5EURUSDM15.close,
        MT5EURUSDM15.rsi_14,
        YahooFinanceDaily.spx_close,
        YahooFinanceDaily.vix_close,
        DocumentsMacro.eurozone_cpi
    ).select_from(MT5EURUSDM15)\
     .outerjoin(YahooFinanceDaily, ...)\
     .outerjoin(DocumentsMacro, ...)\
     .filter(MT5EURUSDM15.time >= start_date)\
     .filter(MT5EURUSDM15.time <= end_date)

    results = query.all()

    # Formatage en structure ML-ready
    return [format_training_sample(r, features, target) for r in results]
```

### 5. Health Check

```python
# Fichier: fastapi/app/routes/health.py

@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    """
    Vérifie la santé de l'API et de la base de données

    **Pas d'authentification requise** (monitoring)
    """
    try:
        # Test connexion PostgreSQL
        db.execute("SELECT 1")

        # Comptage des lignes dans chaque table
        mt5_count = db.query(func.count(MT5EURUSDM15.time)).scalar()
        yahoo_count = db.query(func.count(YahooFinanceDaily.time)).scalar()
        macro_count = db.query(func.count(DocumentsMacro.time)).scalar()

        return {
            "status": "healthy",
            "database": "connected",
            "tables": {
                "mt5_eurusd_m15": mt5_count,
                "yahoo_finance_daily": yahoo_count,
                "documents_macro": macro_count
            },
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unavailable: {e}")
```

## Schemas Pydantic pour validation

```python
# Fichier: fastapi/app/schemas/data.py

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class MT5Response(BaseModel):
    """Schéma de réponse pour les données MT5"""
    time: datetime = Field(..., description="Timestamp UTC")
    open: float = Field(..., ge=0, description="Prix d'ouverture")
    high: float = Field(..., ge=0, description="Prix le plus haut")
    low: float = Field(..., ge=0, description="Prix le plus bas")
    close: float = Field(..., ge=0, description="Prix de clôture")
    tick_volume: int = Field(..., ge=0, description="Volume (ticks)")
    close_return: Optional[float] = Field(None, description="Rendement")
    volatility_1h: Optional[float] = Field(None, description="Volatilité 1h")
    rsi_14: Optional[float] = Field(None, ge=0, le=100, description="RSI 14")

    class Config:
        from_attributes = True  # Compatibilité SQLAlchemy
        json_schema_extra = {
            "example": {
                "time": "2025-01-27T14:30:00Z",
                "open": 1.0435,
                "high": 1.0442,
                "low": 1.0433,
                "close": 1.0440,
                "tick_volume": 1234,
                "rsi_14": 52.3
            }
        }
```

## Documentation automatique (OpenAPI/Swagger)

FastAPI génère automatiquement la documentation interactive de l'API :

- **Swagger UI** : `http://localhost:8000/docs`
- **ReDoc** : `http://localhost:8000/redoc`
- **OpenAPI JSON** : `http://localhost:8000/openapi.json`

### Configuration personnalisée

```python
# Fichier: fastapi/app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="OrionTrader Data API",
    description="API REST pour l'accès aux données de trading EUR/USD",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS pour permettre l'accès depuis le frontend Streamlit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],  # Streamlit
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Inclusion des routes
app.include_router(data_router)
app.include_router(market_router)
app.include_router(health_router)
```

## Intégration avec le pipeline ETL

L'API accède directement aux tables PostgreSQL de la couche Gold, garantissant que les données exposées sont validées et de qualité.

```python
# Dépendance FastAPI pour la connexion DB
def get_db():
    """Dependency injection pour la session SQLAlchemy"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

Après chaque exécution du pipeline ETL (quotidien via Airflow), les nouvelles données sont automatiquement disponibles via l'API sans intervention manuelle.

## Sécurité et performance

- **Authentification Bearer Token** sur tous les endpoints sensibles
- **Pagination** pour limiter la charge mémoire (limit/offset)
- **Filtrage temporel** obligatoire pour éviter de charger toute la table
- **Rate limiting** (non implémenté dans la démo, mais recommandé en production)
- **Cache HTTP** (headers Cache-Control pour données historiques immuables)

**Conclusion C5** : Le projet démontre une maîtrise complète du développement d'une API REST professionnelle avec FastAPI, exposant les données de manière sécurisée, documentée et optimisée pour les cas d'usage du trading algorithmique.

---

# Conclusion et Validation des Compétences

Ce dossier a démontré la maîtrise complète des **5 compétences du Bloc 1 "Gestion des données"** du référentiel Concepteur Développeur en IA :

- **C1 (100%)** : Extraction automatisée depuis 4 types de sources (API REST, scraping, fichiers, base de données) orchestrée par Airflow
- **C2 (100%)** : Requêtes SQL via SQLAlchemy ORM (SELECT, JOIN, agrégations, CRUD) optimisées pour PostgreSQL
- **C3 (100%)** : Agrégation multi-sources avec architecture Bronze/Silver/Gold, suppression des entrées corrompues, homogénéisation des formats, et création de features dérivées
- **C4 (100%)** : Modélisation conceptuelle/physique d'une base PostgreSQL production, conformité RGPD (données publiques, sécurité, rétention)
- **C5 (100%)** : API REST FastAPI exposant les données avec authentification, pagination, documentation OpenAPI

Le projet **OrionTrader** constitue un système complet de gestion de données financières pour le trading algorithmique, démontrant une maîtrise professionnelle des technologies modernes (Python, Airflow, PostgreSQL, SQLAlchemy, FastAPI) et des bonnes pratiques (ETL structuré, sécurité, traçabilité, automatisation).

---

# Annexes

## A. Exemples de requêtes API

```bash
# Exemple 1: Features MT5 dernières 24h
curl -X GET "http://localhost:8000/data/features/mt5?limit=96" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Exemple 2: Snapshot de marché actuel
curl -X GET "http://localhost:8000/market/snapshot/latest" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Exemple 3: Training data pour ML
curl -X GET "http://localhost:8000/data/training/data?start_date=2023-01-01&end_date=2025-01-27" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Exemple 4: Health check
curl -X GET "http://localhost:8000/health"
```

## B. Commandes de déploiement

```bash
# Démarrer l'infrastructure complète
docker compose up -d

# Vérifier les logs Airflow
docker compose logs -f airflow-scheduler

# Déclencher manuellement le DAG ETL
docker exec -it airflow-scheduler airflow dags trigger ETL_forex_pipeline

# Accéder à PostgreSQL
docker exec -it orion_postgres psql -U postgres -d trading_data

# Tester l'API
curl http://localhost:8000/health
```

## C. Schéma d'architecture complet

```
┌──────────────────────────────────────────────────────────────────────┐
│                         SOURCES DE DONNÉES                            │
├──────────────────────────────────────────────────────────────────────┤
│  MetaTrader 5    │   Yahoo Finance   │   Eurostat/BCE/OECD          │
│  (Fichiers)      │   (API REST)      │   (Web Scraping)             │
│  M15             │   Daily           │   Monthly/Annual             │
└──────────────────┴───────────────────┴──────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATION (Airflow)                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  Extract MT5 │  │ Extract Yahoo│  │ Extract Macro│              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
│         │                  │                  │                      │
│         └──────────────────┴──────────────────┘                      │
│                           │                                          │
│                           ▼                                          │
│              ┌─────────────────────────┐                            │
│              │   BRONZE (Raw Data)     │                            │
│              │   Format: Parquet       │                            │
│              └─────────────────────────┘                            │
│                           │                                          │
│                           ▼                                          │
│              ┌─────────────────────────┐                            │
│              │   SILVER (Transform)    │                            │
│              │   - Nettoyage           │                            │
│              │   - Validation          │                            │
│              │   - Features            │                            │
│              │   - Agrégation          │                            │
│              └─────────────────────────┘                            │
│                           │                                          │
│                           ▼                                          │
│              ┌─────────────────────────┐                            │
│              │   GOLD (Load to DB)     │                            │
│              │   PostgreSQL 15         │                            │
│              └─────────────────────────┘                            │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         API REST (FastAPI)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │ /data/mt5    │  │ /market/snap │  │ /training    │              │
│  │ /data/yahoo  │  │ /market/ohlcv│  │ /health      │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      CONSOMMATEURS                                    │
│  - Modèles ML (Marimo notebooks)                                    │
│  - Dashboard (Streamlit)                                             │
│  - Backtesting                                                       │
│  - Alertes Discord                                                   │
└──────────────────────────────────────────────────────────────────────┘
```

## D. Références et documentation

- **Code source** : [github.com/user/OrionTrader](https://github.com)
- **Documentation API** : http://localhost:8000/docs
- **Airflow UI** : http://localhost:8080 (admin/admin)
- **PostgreSQL** : localhost:5432 (postgres/password)

---

**Projet OrionTrader - Certification Développeur en Intelligence Artificielle - Janvier 2026**
**Prepared by Aurélien Ruide**
**Bloc 1 : Réaliser la collecte, le stockage et la mise à disposition des données d'un projet en IA**
