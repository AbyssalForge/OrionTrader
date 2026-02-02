# 📊 Wikipedia Scraping - Référentiel des Indices Boursiers

## 🎯 Objectif

Scraper les composants des principaux indices boursiers depuis Wikipedia pour créer un référentiel marché permettant le mapping `ticker → secteur/pays/indice`.

## 📁 Architecture Ajoutée

### Bronze Layer (Extraction)
**Fichier**: `services/scraping_service.py`
- Scraping des 4 indices principaux:
  - **CAC 40** (France)
  - **S&P 500** (USA)
  - **NASDAQ 100** (USA)
  - **Dow Jones Industrial Average** (USA)

**Fonction**: `extract_wikipedia_indices()` dans `bronze_service.py`
- Sauvegarde dans `data/wikipedia/*.parquet`

### Silver Layer (Transformation)
**Fichier**: `services/silver_service.py`
**Fonction**: `transform_wikipedia_features()`

Transformations appliquées:
- Nettoyage des tickers (suppression références, espaces)
- Standardisation des secteurs
- Dédoublonnage (garder première occurrence par ticker)
- Ajout région (Europe, North America, Other)
- Création `ticker_company` (ex: "AAPL - Apple Inc.")
- Indicateur multi-indices (entreprises dans plusieurs indices)

### Gold Layer (Chargement)
**Fichier**: `services/gold_service.py`
**Fonction**: `load_wikipedia_to_db()`

**Table PostgreSQL**: `wikipedia_indices`

### Modèle de Données
**Fichier**: `models/WikipediaIndices.py`

```sql
CREATE TABLE wikipedia_indices (
    ticker VARCHAR(20) PRIMARY KEY,           -- Ticker unique
    company_name VARCHAR(200) NOT NULL,       -- Nom de l'entreprise
    sector VARCHAR(100),                      -- Secteur (Technology, Finance, etc.)
    country VARCHAR(100),                     -- Pays (USA, France, etc.)
    region VARCHAR(100),                      -- Région (Europe, North America)
    index_name VARCHAR(100),                  -- Premier indice
    index_key VARCHAR(50),                    -- Clé indice (CAC40, SP500, etc.)
    num_indices INTEGER,                      -- Nombre d'indices
    is_multi_index BOOLEAN,                   -- Présent dans >1 indice
    ticker_company VARCHAR(250),              -- "AAPL - Apple Inc."
    scraped_at TIMESTAMP WITH TIME ZONE,      -- Date scraping
    transformed_at TIMESTAMP WITH TIME ZONE,  -- Date transformation
    created_at TIMESTAMP WITH TIME ZONE,      -- Date création en BDD
    pipeline_run_id VARCHAR(100)              -- ID du run pipeline
);
```

**Indexes**:
- `idx_wiki_ticker` (ticker)
- `idx_wiki_sector` (sector)
- `idx_wiki_country` (country)
- `idx_wiki_index` (index_key)
- `idx_wiki_pipeline` (pipeline_run_id)

## 🔄 Architecture des Pipelines

### DAG Séparé - `wikipedia_scraping_pipeline.py`

Le scraping Wikipedia est maintenant dans un **DAG séparé** car les données changent rarement:

```
┌─────────────┐
│ Initialize  │
└──────┬──────┘
       │
       v
┌─────────────┐
│ Extract Wiki│
│  (4 indices)│
└──────┬──────┘
       │
       v
┌─────────────┐
│ Transform   │
│  Wikipedia  │
└──────┬──────┘
       │
       v
┌─────────────┐
│    Load     │
│  Wikipedia  │
└──────┬──────┘
       │
       v
┌─────────────┐
│  Validate   │
│  Wikipedia  │
└─────────────┘
```

### DAG Principal - `etl_forex_pipeline.py`

Le pipeline quotidien gère les 4 autres tables:

```
┌─────────────┐
│ Initialize  │
└──────┬──────┘
       │
       v
┌─────────────┐
│ Extract MT5 │
│Extract Yahoo│
│Extract Docs │
└──────┬──────┘
       │
       v
┌─────────────┐
│Transform MT5│
│TransformYaho│
│TransformDocs│
└──────┬──────┘
       │
       v
┌─────────────┐
│  Load MT5   │
│  Load Yahoo │
│  Load Docs  │
│Load Snapshot│
└──────┬──────┘
       │
       v
┌─────────────┐
│  Validate   │
│  (4 tables) │
└──────┬──────┘
       │
       v
┌─────────────┐
│   Notify    │
│  (Discord)  │
└─────────────┘
```

### Fréquence de Scraping

**Wikipedia Pipeline:**
- **Mode**: Manuel (schedule=None) ou configurable
- **Recommandé**: Hebdomadaire ou mensuel
- **Raison**: Les composants d'indices changent rarement
- **Configuration**:
  - Manuel: Lancer depuis l'UI Airflow
  - Hebdomadaire: Décommenter `schedule='0 2 * * 0'`
  - Mensuel: Décommenter `schedule='0 2 1 * *'`

**Pipeline Principal (ETL Forex):**
- **Mode**: Quotidien à 18h00 UTC
- **Gère**: MT5, Yahoo, Documents, Market Snapshot

### Indépendance des Pipelines

Les deux pipelines sont **complètement indépendants**:
- Wikipedia: Scraping occasionnel (hebdo/mensuel/manuel)
- ETL Forex: Extraction quotidienne (18h00 UTC)
- Pas de dépendance entre les deux
- Table `wikipedia_indices` reste disponible pour les jointures SQL

## 📊 Données Collectées

### Statistiques attendues

| Indice | Nombre d'entreprises | Secteurs |
|--------|---------------------|----------|
| CAC 40 | ~40 | 10+ |
| S&P 500 | ~500 | 11 (GICS) |
| NASDAQ 100 | ~100 | 8+ |
| Dow Jones | ~30 | 10+ |
| **TOTAL** | **~670 tickers uniques** | **~11 secteurs** |

### Secteurs GICS (S&P 500)

1. Information Technology
2. Healthcare
3. Financials
4. Consumer Discretionary
5. Consumer Staples
6. Industrials
7. Energy
8. Materials
9. Real Estate
10. Communication Services
11. Utilities

## 🔍 Cas d'Usage

### 1. Mapping Ticker → Secteur

```python
from sqlalchemy import create_engine
import pandas as pd

engine = create_engine("postgresql://...")

# Récupérer mapping
df_mapping = pd.read_sql("""
    SELECT ticker, company_name, sector, country, index_name
    FROM wikipedia_indices
    ORDER BY ticker
""", engine)

# Utiliser le mapping
ticker_to_sector = dict(zip(df_mapping['ticker'], df_mapping['sector']))
print(ticker_to_sector['AAPL'])  # "Technology"
```

### 2. Analyse par Secteur

```sql
-- Distribution par secteur
SELECT
    sector,
    COUNT(*) as num_companies,
    ARRAY_AGG(DISTINCT index_name) as indices
FROM wikipedia_indices
GROUP BY sector
ORDER BY num_companies DESC;
```

### 3. Entreprises Multi-Indices

```sql
-- Entreprises présentes dans plusieurs indices
SELECT
    ticker,
    company_name,
    num_indices,
    index_name
FROM wikipedia_indices
WHERE is_multi_index = TRUE
ORDER BY num_indices DESC;
```

### 4. Filtrage par Pays/Région

```sql
-- Entreprises françaises
SELECT ticker, company_name, sector
FROM wikipedia_indices
WHERE country = 'France';

-- Entreprises européennes
SELECT ticker, company_name, country, sector
FROM wikipedia_indices
WHERE region = 'Europe';
```

## 🛠️ Installation

### Dépendances Python

Ajoutez au `requirements.txt` d'Airflow:

```txt
beautifulsoup4>=4.12.0
requests>=2.31.0
lxml>=4.9.0
html5lib>=1.1
```

Installation:
```bash
cd airflow
pip install beautifulsoup4 requests lxml html5lib
```

### Migration Base de Données

La table `wikipedia_indices` sera créée automatiquement au premier run via:
```python
from models import create_all_tables
create_all_tables()
```

Ou manuellement dans PostgreSQL:
```sql
-- Voir le modèle dans models/WikipediaIndices.py
```

## 🚀 Utilisation

### Lancer le DAG Wikipedia

Le scraping Wikipedia est maintenant dans un DAG séparé:

```bash
# Depuis Airflow UI ou CLI
airflow dags trigger wikipedia_scraping_pipeline

# Le pipeline ne nécessite aucun paramètre (pas de dates)
# Il scrape toujours les données actuelles des 4 indices
```

**Interface Airflow:**
1. Ouvrir l'UI Airflow (http://localhost:8080)
2. Rechercher `wikipedia_scraping_pipeline`
3. Cliquer sur "Trigger DAG" (icône ▶️)
4. Pas de paramètres requis - cliquer directement sur "Trigger"

**Note:** Le pipeline principal `ETL_forex_pipeline` ne scrape plus Wikipedia.

### Vérifier les Résultats

```sql
-- Nombre de tickers chargés
SELECT COUNT(*) FROM wikipedia_indices;

-- Dernière mise à jour
SELECT MAX(created_at) FROM wikipedia_indices;

-- Top 10 secteurs
SELECT sector, COUNT(*) as count
FROM wikipedia_indices
GROUP BY sector
ORDER BY count DESC
LIMIT 10;
```

## 📈 Monitoring

### Logs Airflow

```bash
# Logs de scraping
docker logs airflow-worker | grep SCRAPING

# Logs de transformation
docker logs airflow-worker | grep WIKIPEDIA

# Validation
docker logs airflow-worker | grep VALIDATE
```

### Métriques

Les métriques suivantes sont trackées:
- ✅ Nombre de tickers scrapés
- ✅ Nombre de secteurs uniques
- ✅ Nombre de pays uniques
- ✅ Tickers multi-indices
- ✅ Durée de scraping
- ✅ Statut de validation

## ⚠️ Limitations et Considérations

### Légalité

✅ **Wikipedia est sous licence CC-BY-SA**
- Scraping autorisé tant que:
  - Attribution donnée (Wikipedia)
  - Pas d'abus (rate limiting respecté)
  - Usage non commercial (OrionTrader = projet perso/éducatif)

### Rate Limiting

- **Pause entre requêtes**: 1 seconde
- **User-Agent**: Identifié comme navigateur standard
- **Timeout**: 30 secondes par requête
- **Gestion d'erreurs**: Continue si une page échoue

### Maintenance

⚠️ **Structure HTML peut changer**
- Les tables Wikipedia peuvent changer de format
- Testez régulièrement le scraping
- Vérifiez les colonnes disponibles

**Solution**:
- Logs détaillés en cas d'échec
- Tests unitaires sur la structure HTML
- Fallback sur données anciennes si échec

### Mises à Jour

- **CAC 40**: Change ~1-2 fois/an
- **S&P 500**: Change ~20-30 fois/an (ajouts/retraits)
- **NASDAQ 100**: Change ~10-15 fois/an
- **Dow Jones**: Change très rarement (~1-2 fois/an)

**Recommandation**: Scraper 1x/semaine ou 1x/mois selon besoins

## 🔧 Configuration Avancée

### Ajouter d'Autres Indices

Modifiez `services/scraping_service.py`:

```python
INDICES_CONFIG = {
    # ... indices existants ...

    'FTSE100': {
        'url': 'https://en.wikipedia.org/wiki/FTSE_100_Index',
        'table_index': 1,
        'columns_mapping': {
            'Company': 'company_name',
            'Ticker': 'ticker',
            'Sector': 'sector'
        },
        'country_default': 'UK',
        'index_name': 'FTSE 100'
    }
}
```

### Personnaliser la Fréquence

Le DAG `wikipedia_scraping_pipeline.py` est configuré en mode **manuel** par défaut.

Pour activer une exécution automatique, modifiez le paramètre `schedule` dans le DAG:

**Option 1: Hebdomadaire (Dimanche à 2h00 UTC)**
```python
@dag(
    dag_id='wikipedia_scraping_pipeline',
    schedule='0 2 * * 0',  # Décommenter cette ligne
    # schedule=None,        # Commenter cette ligne
    ...
)
```

**Option 2: Mensuel (1er du mois à 2h00 UTC)**
```python
@dag(
    dag_id='wikipedia_scraping_pipeline',
    schedule='0 2 1 * *',  # Décommenter cette ligne
    # schedule=None,        # Commenter cette ligne
    ...
)
```

**Option 3: Bimensuel (1er et 15 du mois)**
```python
@dag(
    dag_id='wikipedia_scraping_pipeline',
    schedule='0 2 1,15 * *',
    ...
)
```

**Recommandation:**
- **Hebdomadaire** si vous tradez sur indices US (S&P 500 change ~2x/mois)
- **Mensuel** si vous tradez surtout EURUSD (CAC 40 change rarement)
- **Manuel** pour contrôle total (lancer quand nécessaire)

## 📚 Ressources

- **Wikipedia Terms**: https://en.wikipedia.org/wiki/Wikipedia:Copyrights
- **BeautifulSoup Docs**: https://www.crummy.com/software/BeautifulSoup/
- **GICS Sectors**: https://www.msci.com/gics

## ✅ Checklist de Validation

- [x] Dépendances installées (beautifulsoup4, lxml, html5lib)
- [x] Table `wikipedia_indices` créée en PostgreSQL
- [x] DAG séparé `wikipedia_scraping_pipeline.py` créé
- [x] DAG principal `ETL_forex_pipeline.py` mis à jour (Wikipedia retiré)
- [ ] Premier run réussi (>600 tickers chargés)
- [ ] Validation Wikipedia OK
- [ ] Logs sans erreur pour [SCRAPING], [WIKIPEDIA], [VALIDATE]
- [ ] Mapping ticker→secteur fonctionnel

---

**Status**: ✅ Implémenté avec DAG séparé (v3.1)
**Date**: 2026-01-31
**Architecture**:
- **Pipeline quotidien** (`etl_forex_pipeline.py`): 4 tables
  - mt5_eurusd_m15, yahoo_finance_daily, documents_macro, market_snapshot_m15
- **Pipeline Wikipedia** (`wikipedia_scraping_pipeline.py`): 1 table
  - wikipedia_indices (manuel/hebdo/mensuel)
