# Configuration des dates pour le pipeline ETL

## Vue d'ensemble

Le pipeline ETL permet de configurer les dates d'extraction lors du lancement manuel, ce qui est idéal pour le **backtesting** sur des périodes historiques spécifiques.

## Dates configurables

### MT5 (MetaTrader 5)
- `start_mt5`: Date de début pour MT5 (format: `YYYY-MM-DD`)
- `end_mt5`: Date de fin pour MT5 (format: `YYYY-MM-DD`)
- **Timeframe**: M15 (15 minutes)
- **Par défaut**: J-2 → J-1 (avant-hier → hier)
- **Pourquoi J-1**: Évite les erreurs MT5 avec données incomplètes du jour actuel

### Yahoo Finance
- `start_yahoo`: Date de début pour Yahoo Finance (format: `YYYY-MM-DD`)
- `end_yahoo`: Date de fin pour Yahoo Finance (format: `YYYY-MM-DD`)
- **Timeframe**: 1D (daily)
- **Par défaut**: J-2 → J-1 (avant-hier → hier)
- **Pourquoi J-1**: Données complètes et finalisées de la veille

### Documents macro (Eurostat, OECD, World Bank)
- `start_document`: Date de début pour les documents (format: `YYYY-MM-DD`)
- **Date de fin**: Toujours aujourd'hui (données macro actuelles)
- **Fréquence**: Mensuelle/Trimestrielle
- **Par défaut**: 5 ans avant aujourd'hui
- **Important**: Utiliser minimum 5 ans (données macro peu fréquentes)

## Comment modifier les dates

> **Note importante**: Pour l'exécution quotidienne automatique (schedule 18h UTC), les dates par défaut sont J-2→J-1 pour MT5/Yahoo et 5 ans pour Documents. Vous n'avez besoin de modifier les dates que pour du **backtesting** manuel sur des périodes spécifiques.

### Option 1: Via l'interface Airflow UI

1. Aller dans l'interface Airflow
2. Cliquer sur le DAG `ETL_forex_pipeline`
3. Cliquer sur "Trigger DAG" (bouton ▶️)
4. Dans la fenêtre qui s'ouvre, cliquer sur "Trigger DAG w/ config"
5. Modifier les paramètres JSON:

```json
{
  "start_mt5": "2024-01-01",
  "end_mt5": "2024-12-31",
  "start_yahoo": "2024-01-01",
  "end_yahoo": "2024-12-31",
  "start_document": "2020-01-01"
}
```

6. Cliquer sur "Trigger"

### Option 2: Via la CLI Airflow

```bash
airflow dags trigger ETL_forex_pipeline \
  --conf '{
    "start_mt5": "2024-01-01",
    "end_mt5": "2024-12-31",
    "start_yahoo": "2024-01-01",
    "end_yahoo": "2024-12-31",
    "start_document": "2020-01-01"
  }'
```

### Option 3: Modifier les valeurs par défaut dans le code

Éditer le fichier [etl_forex_pipeline.py](etl_forex_pipeline.py):

```python
# Dates par défaut (lignes 47-56)
DEFAULT_DATE_NOW = datetime.now()
DEFAULT_DATE_START = DEFAULT_DATE_NOW - timedelta(days=730)  # Modifier ici

DEFAULT_START_MT5 = DEFAULT_DATE_START
DEFAULT_START_YAHOO = DEFAULT_DATE_START
DEFAULT_START_DOCUMENT = DEFAULT_DATE_NOW - timedelta(days=1825)

DEFAULT_END_MT5 = DEFAULT_DATE_NOW
DEFAULT_END_YAHOO = DEFAULT_DATE_NOW
DEFAULT_END_DOCUMENT = DEFAULT_DATE_NOW
```

## Exemples d'utilisation

### Exemple 1: Backtesting sur l'année 2024

```json
{
  "start_mt5": "2024-01-01",
  "end_mt5": "2024-12-31",
  "start_yahoo": "2024-01-01",
  "end_yahoo": "2024-12-31",
  "start_document": "2019-01-01"
}
```

**Résultat attendu:**
- MT5: ~17,500 lignes (252 jours × 96 barres M15/jour)
- Yahoo: ~252 lignes (jours de trading)
- Documents: ~60 lignes (5 ans de données mensuelles/trimestrielles)

### Exemple 2: Test sur un mois spécifique

```json
{
  "start_mt5": "2024-06-01",
  "end_mt5": "2024-06-30",
  "start_yahoo": "2024-06-01",
  "end_yahoo": "2024-06-30",
  "start_document": "2019-06-01"
}
```

**Résultat attendu:**
- MT5: ~2,000 lignes (21 jours × 96 barres M15/jour)
- Yahoo: ~21 lignes (jours de trading)
- Documents: ~60 lignes (5 ans de données)

### Exemple 3: Test sur une semaine (day trading)

```json
{
  "start_mt5": "2024-11-01",
  "end_mt5": "2024-11-08",
  "start_yahoo": "2024-11-01",
  "end_yahoo": "2024-11-08",
  "start_document": "2019-11-01"
}
```

**Résultat attendu:**
- MT5: ~480 lignes (5 jours × 96 barres M15/jour)
- Yahoo: ~5 lignes (jours de trading)
- Documents: ~60 lignes (5 ans de données)

## Notes importantes

### Limitations Yahoo Finance intraday
- Yahoo Finance limite les données **intraday** (M1, M5, M15, etc.) à environ **60 jours**
- Pour des périodes > 60 jours, Yahoo utilise automatiquement des intervalles plus longs
- **Recommandation**: Utilisez des périodes ≤ 60 jours si vous voulez des données M15 de Yahoo

### MT5 vs Yahoo timeframe
- **MT5**: M15 (granularité intraday pour le trading)
- **Yahoo**: 1D (contexte macro daily)
- Les deux sont mergés avec `merge_asof` dans la couche Silver

### Documents macro
- Les documents ont une fréquence **mensuelle/trimestrielle**
- La période par défaut de 5 ans capture assez de données macro
- La date de fin est toujours aujourd'hui pour avoir les données les plus récentes

## Architecture du pipeline

```
┌─────────────────────────────────────────────────────────┐
│ CONFIGURATION (modifiable au lancement)                 │
├─────────────────────────────────────────────────────────┤
│ • start_mt5 / end_mt5          (M15)                   │
│ • start_yahoo / end_yahoo      (1D)                    │
│ • start_document               (Monthly/Quarterly)     │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ BRONZE (Extraction)                                      │
├─────────────────────────────────────────────────────────┤
│ • MT5: data/mt5/eurusd.parquet                          │
│ • Yahoo: data/api/{asset}.parquet (9 actifs)           │
│ • Documents: data/documents/{source}.parquet            │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ SILVER (Transformation)                                  │
├─────────────────────────────────────────────────────────┤
│ • MT5: Features calculés                                │
│ • Yahoo: Normalization + merge (outer join)            │
│ • Documents: Pivot + features                           │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ GOLD (Load Database)                                     │
├─────────────────────────────────────────────────────────┤
│ • mt5_eurusd_m15                                        │
│ • yahoo_finance_daily                                   │
│ • documents_macro                                       │
└─────────────────────────────────────────────────────────┘
```

## Troubleshooting

### Problème: Pas de données Yahoo pour une période ancienne
**Solution**: Yahoo Finance peut ne pas avoir de données pour certains actifs avant 2010. Vérifiez la disponibilité des données sur finance.yahoo.com

### Problème: Trop de lignes MT5 pour une longue période
**Solution**: MT5 en M15 génère 96 barres/jour × 252 jours/an = ~24,000 lignes/an. Pour de longues périodes, considérez D1 au lieu de M15.

### Problème: Peu de lignes pour Documents
**Solution**: Normal, les documents ont une fréquence mensuelle/trimestrielle. 5 ans = ~60 lignes de CPI mensuel + ~20 lignes de PIB trimestriel.

## Validation des données

Le pipeline valide automatiquement:
- **MT5**: > 500 lignes attendues (pour 2 ans D1)
- **Yahoo**: > 500 lignes attendues (pour 2 ans D1)
- **Documents**: > 20 lignes attendues (pour 5 ans)

Les seuils sont adaptés automatiquement selon les périodes configurées.
