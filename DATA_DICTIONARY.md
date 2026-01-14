# Dictionnaire de Données - OrionTrader Pipeline v3.0

## Vue d'ensemble

Pipeline ETL avec architecture 4 tables :
- **3 tables sources** : MT5, Yahoo Finance, Documents (données brutes + features)
- **1 table composite** : Market Snapshot (foreign keys + features calculées)

---

## Table 1/4 : `mt5_eurusd_m15`

### Description
Source de données haute fréquence provenant du serveur MetaTrader 5 local.

### Métadonnées
| Propriété | Valeur |
|-----------|---------|
| **Source** | Serveur MetaTrader 5 local (Pyro5) |
| **Fréquence** | M15 (15 minutes) |
| **Volume** | ~70,000 lignes pour 2 ans |
| **Taille estimée** | ~20 MB |
| **Type** | Prix OHLCV + Microstructure |

### Colonnes (17 total)

#### OHLCV Raw Data (6 colonnes)
| Colonne | Type | Description | Nullable |
|---------|------|-------------|----------|
| `time` | DateTime(TZ) | **Primary Key** - Timestamp UTC de la bougie M15 | Non |
| `open` | Float | Prix d'ouverture | Non |
| `high` | Float | Prix le plus haut | Non |
| `low` | Float | Prix le plus bas | Non |
| `close` | Float | Prix de clôture | Non |
| `tick_volume` | Float | Volume de ticks (indicatif) | Oui |

#### Features Microstructure (11 colonnes)

**Variations de prix** (3 colonnes)
| Colonne | Type | Description | Formule |
|---------|------|-------------|---------|
| `close_diff` | Float | Différence absolue close vs close précédent | `close - close[-1]` |
| `close_return` | Float | Return % close vs close précédent | `(close - close[-1]) / close[-1] * 100` |
| `high_low_range` | Float | Range high-low de la bougie | `high - low` |

**Volatilité multi-horizon** (2 colonnes)
| Colonne | Type | Description | Fenêtre | Formule |
|---------|------|-------------|---------|---------|
| `volatility_1h` | Float | Volatilité 1 heure | 4 bougies M15 | `std(close_return, 4)` |
| `volatility_4h` | Float | Volatilité 4 heures | 16 bougies M15 | `std(close_return, 16)` |

**Momentum multi-horizon** (3 colonnes)
| Colonne | Type | Description | Fenêtre | Formule |
|---------|------|-------------|---------|---------|
| `momentum_15m` | Float | Momentum 15 minutes | 1 bougie | `(close - close[-1]) / close[-1]` |
| `momentum_1h` | Float | Momentum 1 heure | 4 bougies | `(close - close[-4]) / close[-4]` |
| `momentum_4h` | Float | Momentum 4 heures | 16 bougies | `(close - close[-16]) / close[-16]` |

**Analyse chandelier** (3 colonnes)
| Colonne | Type | Description | Formule |
|---------|------|-------------|---------|
| `body` | Float | Taille du corps de la bougie | `abs(close - open)` |
| `upper_shadow` | Float | Longueur mèche haute | `high - max(open, close)` |
| `lower_shadow` | Float | Longueur mèche basse | `min(open, close) - low` |

#### Metadata (2 colonnes)
| Colonne | Type | Description |
|---------|------|-------------|
| `created_at` | DateTime(TZ) | Timestamp création ligne |
| `pipeline_run_id` | String(100) | ID du run pipeline |

### Index
- `idx_mt5_time` : Index sur `time`
- `idx_mt5_pipeline` : Index sur `pipeline_run_id`

### Utilisation ML
- **Features de base** pour tous les modèles
- **Capture la microstructure** de marché haute fréquence
- **Volatilité et momentum** pour détection de régimes

---

## Table 2/4 : `yahoo_finance_daily`

### Description
Indices financiers quotidiens pour contexte macro-économique.

### Métadonnées
| Propriété | Valeur |
|-----------|---------|
| **Source** | Yahoo Finance API (yfinance) |
| **Fréquence** | Daily (quotidien) |
| **Volume** | ~500 lignes pour 2 ans |
| **Taille estimée** | ~50 KB |
| **Type** | Indices financiers + Régime de marché |

### Colonnes (14 total)

#### S&P 500 - Appétit pour le risque (3 colonnes)
| Colonne | Type | Description | Formule/Seuil |
|---------|------|-------------|---------------|
| `spx_close` | Float | Niveau S&P 500 (prix de clôture) | - |
| `spx_trend` | Float | Tendance court terme | `pct_change(5 jours)` |
| `risk_on` | Integer | Binaire : appétit pour le risque | `1 si spx_trend > 0, sinon 0` |

#### Gold - Safe Haven (3 colonnes)
| Colonne | Type | Description | Formule/Seuil |
|---------|------|-------------|---------------|
| `gold_close` | Float | Prix de l'or (USD/oz) | - |
| `gold_trend` | Float | Tendance court terme | `pct_change(5 jours)` |
| `safe_haven` | Integer | Binaire : fuite vers la sécurité | `1 si gold_trend > 0, sinon 0` |

#### DXY (Dollar Index) - Force du dollar (4 colonnes)
| Colonne | Type | Description | Formule/Seuil |
|---------|------|-------------|---------------|
| `dxy_close` | Float | Niveau DXY (indice dollar) | - |
| `dxy_trend_1h` | Float | Tendance court terme | `pct_change(1 jour)` |
| `dxy_trend_4h` | Float | Tendance moyen terme | `pct_change(5 jours)` |
| `dxy_strength` | Float | Force relative du dollar | `(dxy_close - MA20) / MA20` |

#### VIX (Volatilité) - Stress de marché (4 colonnes)
| Colonne | Type | Description | Formule/Seuil |
|---------|------|-------------|---------------|
| `vix_close` | Float | Niveau VIX (indice de volatilité) | - |
| `vix_level` | Float | Niveau relatif | `(vix_close - MA20) / MA20` |
| `vix_change` | Float | Variation quotidienne | `pct_change(1 jour)` |
| `market_stress` | Integer | Binaire : stress de marché | `1 si vix_close > 20, sinon 0` |

#### Metadata (2 colonnes)
| Colonne | Type | Description |
|---------|------|-------------|
| `created_at` | DateTime(TZ) | Timestamp création ligne |
| `pipeline_run_id` | String(100) | ID du run pipeline |

### Index
- `idx_yahoo_time` : Index sur `time`
- `idx_yahoo_pipeline` : Index sur `pipeline_run_id`

### Actifs suivis
| Actif | Ticker Yahoo | Description |
|-------|--------------|-------------|
| EUR/USD | `EURUSD=X` | Paire de devises principale |
| GBP/USD | `GBPUSD=X` | Livre sterling |
| USD/JPY | `USDJPY=X` | Yen japonais |
| DXY | `DX-Y.NYB` | Dollar Index |
| S&P 500 | `^GSPC` | Indice actions US |
| VIX | `^VIX` | Volatilité implicite |
| Dow Jones | `^DJI` | Indice industriel US |
| Gold | `GC=F` | Or (futures) |
| Silver | `SI=F` | Argent (futures) |

### Utilisation ML
- **Capture du régime de marché** global (risk-on/risk-off)
- **Contexte macro quotidien** pour EUR/USD
- **Complémentaire aux prix M15** (macro + micro)

---

## Table 3/4 : `documents_macro`

### Description
Données macro-économiques fondamentales (PIB, CPI, Events économiques).

### Métadonnées
| Propriété | Valeur |
|-----------|---------|
| **Sources** | OECD, World Bank, ECB, Investing.com |
| **Fréquence** | Variable (Annual, Monthly, Ponctuel) |
| **Volume** | ~50 lignes pour 2 ans |
| **Taille estimée** | ~10 KB |
| **Type** | Fondamentaux macro-économiques |

### Colonnes (11 total)

#### Identification (2 colonnes)
| Colonne | Type | Description | Valeurs |
|---------|------|-------------|---------|
| `data_type` | String(50) | Type de donnée | `'pib'`, `'cpi'`, `'event'` |
| `frequency` | String(20) | Fréquence de publication | `'annual'`, `'monthly'`, `'punctual'` |

#### PIB Eurozone (3 colonnes)
| Colonne | Type | Description | Formule/Seuil |
|---------|------|-------------|---------------|
| `eurozone_pib` | Float | Croissance PIB % (annual) | Valeur OECD |
| `pib_change` | Float | Variation vs année précédente | `pib - pib[-1]` |
| `pib_growth` | Float | Accélération/décélération | `pib_change - pib_change[-1]` |

#### CPI Eurozone (3 colonnes)
| Colonne | Type | Description | Formule/Seuil |
|---------|------|-------------|---------------|
| `eurozone_cpi` | Float | Inflation CPI % (monthly) | Valeur ECB |
| `cpi_change` | Float | Variation vs mois précédent | `cpi - cpi[-1]` |
| `inflation_pressure` | Integer | Binaire : pression inflationniste | `1 si eurozone_cpi > 2.0, sinon 0` (cible BCE) |

#### Events Économiques (3 colonnes)
| Colonne | Type | Description | Valeurs |
|---------|------|-------------|---------|
| `event_title` | String(200) | Nom de l'événement | Ex: "BCE Rate Decision", "NFP Release" |
| `event_impact` | String(50) | Impact attendu | `'high'`, `'medium'`, `'low'` |
| `event_impact_score` | Float | Score numérique impact | `0.0-1.0` (high=0.8-1.0, medium=0.4-0.7, low=0.0-0.3) |

#### Metadata (2 colonnes)
| Colonne | Type | Description |
|---------|------|-------------|
| `created_at` | DateTime(TZ) | Timestamp création ligne |
| `pipeline_run_id` | String(100) | ID du run pipeline |

### Index
- `idx_documents_time` : Index sur `time`
- `idx_documents_type` : Index sur `data_type`
- `idx_documents_frequency` : Index sur `frequency`
- `idx_documents_pipeline` : Index sur `pipeline_run_id`

### Architecture spécifique
**Fréquence native préservée** : Les données gardent leur fréquence d'origine (annual, monthly, punctual) sans resample ni duplication. La jointure temporelle se fait à l'utilisation ML avec `merge_asof` (backward fill).

**Avantages** :
- ✅ Pas de duplication (PIB pas répété 70k fois)
- ✅ Respect de la fréquence native
- ✅ Facilite l'ajout de nouvelles sources macro
- ✅ Architecture plus propre et maintenable

### Utilisation ML
- **Contexte macro fondamental** (croissance, inflation)
- **Régime économique** (expansion, contraction)
- **Impact événements macro** (fenêtres d'event)

---

## Table 4/4 : `market_snapshot_m15`

### Description
Table de jointure avec foreign keys vers les 3 tables sources + features composites calculées.

### Métadonnées
| Propriété | Valeur |
|-----------|---------|
| **Type** | Table composite (junction + features) |
| **Fréquence** | M15 (15 minutes) - alignée sur MT5 |
| **Volume** | ~70,000 lignes pour 2 ans |
| **Taille estimée** | ~5 MB (léger car pas de duplication) |

### Colonnes (13 total)

#### Primary Key (1 colonne)
| Colonne | Type | Description |
|---------|------|-------------|
| `time` | DateTime(TZ) | **Primary Key** - Timestamp UTC M15 |

#### Foreign Keys (3 colonnes)
| Colonne | Type | Description | Référence |
|---------|------|-------------|-----------|
| `mt5_time` | DateTime(TZ) | FK vers table MT5 | `mt5_eurusd_m15.time` (NOT NULL) |
| `yahoo_time` | DateTime(TZ) | FK vers table Yahoo | `yahoo_finance_daily.time` (nullable) |
| `docs_time` | DateTime(TZ) | FK vers table Documents | `documents_macro.time` (nullable) |

**Note** : `yahoo_time` et `docs_time` sont nullable car les données macro (daily/monthly) ne sont pas présentes à chaque bougie M15. La FK pointe vers la valeur la plus récente (backward fill via `merge_asof`).

#### Features Composites Multi-Sources (2 colonnes)
| Colonne | Type | Description | Valeurs | Calcul |
|---------|------|-------------|---------|--------|
| `macro_micro_aligned` | Integer | Alignement macro/micro | `-1` (bearish EUR), `0` (neutral), `1` (bullish EUR) | `1` si DXY baisse ET EUR/USD hausse<br>`-1` si DXY hausse ET EUR/USD baisse<br>`0` sinon |
| `euro_strength_bias` | Integer | Biais fondamental EUR | `-1` (faible), `0` (neutre), `1` (fort) | `1` si PIB hausse ET risk_on<br>`-1` si PIB baisse ET risk_off<br>`0` sinon |

#### Régimes et Classifications (2 colonnes)
| Colonne | Type | Description | Valeurs | Calcul |
|---------|------|-------------|---------|--------|
| `regime_composite` | String(20) | Régime de marché global | `'risk_on'`, `'risk_off'`, `'neutral'`, `'volatile'` | Basé sur VIX, SPX, Gold:<br>- `risk_on` : VIX < 15 ET risk_on=1<br>- `risk_off` : VIX > 25 ET safe_haven=1<br>- `volatile` : market_stress=1<br>- `neutral` : sinon |
| `volatility_regime` | String(20) | Régime de volatilité | `'low'`, `'normal'`, `'high'` | Basé sur percentile volatility_1h:<br>- `low` : < 50e percentile<br>- `high` : > 150e percentile<br>- `normal` : entre les deux |

#### Scores et Métriques (3 colonnes)
| Colonne | Type | Description | Plage | Calcul |
|---------|------|-------------|-------|--------|
| `signal_confidence_score` | Float | Score de confiance du signal | `0.0` (faible) - `1.0` (fort) | Somme pondérée:<br>- Alignement macro/micro : 0.3<br>- Euro strength bias : 0.3<br>- Volatilité faible : 0.2<br>- Pas de divergence : 0.2 |
| `signal_divergence_count` | Integer | Nombre de divergences détectées | `0` (cohérent) - `3` (confus) | Compte les contradictions:<br>- DXY fort ET EUR fort<br>- risk_on ET safe_haven<br>- Inflation haute ET PIB bas |
| `trend_strength_composite` | Float | Force de la tendance composite | `-1.0` (forte baisse) - `1.0` (forte hausse) | Moyenne pondérée des momentum:<br>`0.2*mom_15m + 0.3*mom_1h + 0.5*mom_4h` |

#### Event Management (1 colonne)
| Colonne | Type | Description | Valeurs | Calcul |
|---------|------|-------------|---------|--------|
| `event_window_active` | Boolean | Fenêtre d'event important | `True` / `False` | `True` si `event_impact_score > 0.7` |

#### Metadata (2 colonnes)
| Colonne | Type | Description |
|---------|------|-------------|
| `created_at` | DateTime(TZ) | Timestamp création ligne |
| `pipeline_run_id` | String(100) | ID du run pipeline |

### Index
| Index | Colonnes | Usage |
|-------|----------|-------|
| `idx_snapshot_time` | `time` | Requêtes temporelles rapides |
| `idx_snapshot_mt5_time` | `mt5_time` | JOINs vers MT5 |
| `idx_snapshot_yahoo_time` | `yahoo_time` | JOINs vers Yahoo |
| `idx_snapshot_docs_time` | `docs_time` | JOINs vers Documents |
| `idx_snapshot_regime` | `regime_composite`, `volatility_regime` | Filtrage par régime |
| `idx_snapshot_confidence` | `signal_confidence_score` | Filtrage par confiance |
| `idx_snapshot_pipeline` | `pipeline_run_id` | Gestion pipeline |

### Architecture et Avantages

**Principe** : Table de jointure avec foreign keys + features calculées (pas de duplication des données sources).

**Avantages** :
- ✅ **Query ML simplifiée** : 1 seul SELECT avec JOINs au lieu de merge complexe
- ✅ **Features pré-calculées** : Pas de calcul à chaque requête
- ✅ **Pas de duplication** : Les colonnes MT5/Yahoo/Docs restent dans leurs tables sources
- ✅ **Identification rapide** : Scores et régimes pour filtrage opportunités
- ✅ **Maintenabilité** : Ajout de features sans toucher aux sources

**Exemple requête ML** :
```sql
SELECT
    s.time,
    s.signal_confidence_score,
    s.regime_composite,
    s.trend_strength_composite,
    m.close, m.volatility_1h,
    y.dxy_close, y.vix_close,
    d.eurozone_pib, d.eurozone_cpi
FROM market_snapshot_m15 s
JOIN mt5_eurusd_m15 m ON s.mt5_time = m.time
LEFT JOIN yahoo_finance_daily y ON s.yahoo_time = y.time
LEFT JOIN documents_macro d ON s.docs_time = d.time
WHERE s.signal_confidence_score > 0.7
  AND s.volatility_regime != 'high'
  AND s.event_window_active = FALSE
ORDER BY s.time DESC
LIMIT 1000;
```

### Utilisation ML
- **Filtrage par régime** : Sélectionner uniquement risk_on/risk_off
- **Filtrage par confiance** : Garder signaux avec score > 0.7
- **Évitement des events** : Exclure les fenêtres d'events à fort impact
- **Détection opportunités** : Alignement macro/micro + faible divergence

---

## Relations entre les tables

```
┌─────────────────────┐
│   mt5_eurusd_m15    │  Table 1: Source MT5 (M15)
│  70k lignes, 20 MB  │  - OHLCV + 11 features microstructure
└──────────┬──────────┘
           │
           │ FK: mt5_time
           │
           ▼
┌─────────────────────┐
│market_snapshot_m15  │  Table 4: Composite (M15)
│  70k lignes, 5 MB   │  - Foreign keys vers 3 sources
└──────────┬──────────┘  - 7 features calculées
           │
           ├──────────────────┐
           │                  │
           │ FK: yahoo_time   │ FK: docs_time
           │                  │
           ▼                  ▼
┌─────────────────────┐  ┌─────────────────────┐
│yahoo_finance_daily  │  │  documents_macro    │
│  500 lignes, 50 KB  │  │  50 lignes, 10 KB   │
└─────────────────────┘  └─────────────────────┘
  Table 2: Yahoo (Daily)   Table 3: Docs (Variable)
  - 4 indices × 2-4 feat.  - PIB, CPI, Events
```

**Jointure temporelle** : Les tables 2 et 3 (daily/monthly) sont jointes à la table 4 (M15) via `merge_asof` avec direction `backward` (forward fill des valeurs macro).

---

## Pipeline ETL - Flow des données

```
BRONZE (Extraction)
  ├─ MT5 Local (Pyro5)         → data/mt5/*.parquet
  ├─ Yahoo Finance (yfinance)  → data/api/*.parquet
  └─ Documents (OECD/WB/ECB)   → data/documents/*.parquet

SILVER (Transformation)
  ├─ MT5 Features              → data/processed/mt5_features.parquet
  ├─ Yahoo Features            → data/processed/yahoo_features.parquet
  ├─ Documents Features        → data/processed/documents_features.parquet
  └─ Market Snapshot           → data/processed/market_snapshot_m15.parquet

GOLD (Load)
  ├─ MT5 → mt5_eurusd_m15
  ├─ Yahoo → yahoo_finance_daily
  ├─ Documents → documents_macro
  └─ Snapshot → market_snapshot_m15

VALIDATION
  └─ Validation des 4 tables → Discord notification
```

---

## Configuration des dates

### MT5 et Yahoo (J-2 → J-1)
```python
DEFAULT_DATE_START = datetime.now() - timedelta(days=2)
DEFAULT_DATE_END = datetime.now() - timedelta(days=1)
```
**Raison** : Évite les données incomplètes du jour J (bougies partielles).

### Documents (5 ans avant)
```python
DEFAULT_DOCUMENT_START = datetime.now() - timedelta(days=1825)  # ~5 ans
```
**Raison** : Les données macro ont une fréquence mensuelle/annuelle. Un seul jour retournerait 0 résultats.

---

## Notes importantes

### ⚠️ Colonnes avec valeurs constantes
Il peut arriver que certaines colonnes aient des valeurs identiques (0 ou constantes) dans les données actuelles. C'est normal si :
- Les conditions de calcul ne sont pas encore remplies (ex: pas d'events à fort impact)
- La période testée est courte (1 jour)
- Le marché est stable (peu de divergences)

Ces colonnes restent utiles pour les analyses long terme et backtesting.

### 🔄 Fréquences multiples
| Table | Fréquence | Lignes/jour (estimé) |
|-------|-----------|----------------------|
| MT5 | M15 | ~96 lignes (24h × 4 bougies/h) |
| Yahoo | Daily | 1 ligne |
| Documents | Variable | 0-1 ligne (selon période) |
| Snapshot | M15 | ~96 lignes (aligné MT5) |

### 📊 Volumétrie totale
| Période | MT5 | Yahoo | Documents | Snapshot | Total |
|---------|-----|-------|-----------|----------|-------|
| 1 jour | ~100 | 1 | 0-1 | ~100 | ~200 |
| 1 an | ~35k | ~250 | ~25 | ~35k | ~70k |
| 2 ans | ~70k | ~500 | ~50 | ~70k | ~140k |

---

## Requêtes SQL utiles

### Statistiques par table
```sql
-- Comptage lignes
SELECT 'mt5' AS table_name, COUNT(*) FROM mt5_eurusd_m15
UNION ALL
SELECT 'yahoo', COUNT(*) FROM yahoo_finance_daily
UNION ALL
SELECT 'documents', COUNT(*) FROM documents_macro
UNION ALL
SELECT 'snapshot', COUNT(*) FROM market_snapshot_m15;

-- Plages temporelles
SELECT
    'mt5' AS table_name,
    MIN(time) AS first_date,
    MAX(time) AS last_date
FROM mt5_eurusd_m15
UNION ALL
SELECT 'yahoo', MIN(time), MAX(time) FROM yahoo_finance_daily
UNION ALL
SELECT 'documents', MIN(time), MAX(time) FROM documents_macro
UNION ALL
SELECT 'snapshot', MIN(time), MAX(time) FROM market_snapshot_m15;
```

### Vérification des foreign keys
```sql
-- Compter les NULL dans les FK (normal pour yahoo/docs car backward fill)
SELECT
    COUNT(*) AS total_rows,
    COUNT(yahoo_time) AS yahoo_matches,
    COUNT(docs_time) AS docs_matches,
    COUNT(*) - COUNT(yahoo_time) AS yahoo_nulls,
    COUNT(*) - COUNT(docs_time) AS docs_nulls
FROM market_snapshot_m15;
```

### Distribution des régimes
```sql
-- Répartition des régimes de marché
SELECT
    regime_composite,
    volatility_regime,
    COUNT(*) AS count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS percentage
FROM market_snapshot_m15
GROUP BY regime_composite, volatility_regime
ORDER BY count DESC;
```

### Signaux haute confiance
```sql
-- Opportunités avec haute confiance + alignement
SELECT
    s.time,
    s.signal_confidence_score,
    s.macro_micro_aligned,
    s.euro_strength_bias,
    s.regime_composite,
    m.close
FROM market_snapshot_m15 s
JOIN mt5_eurusd_m15 m ON s.mt5_time = m.time
WHERE s.signal_confidence_score > 0.7
  AND s.signal_divergence_count = 0
  AND s.event_window_active = FALSE
ORDER BY s.signal_confidence_score DESC, s.time DESC
LIMIT 100;
```

---

## Version et changelog

| Version | Date | Changes |
|---------|------|---------|
| v3.0 | 2026-01-12 | Architecture 4 tables avec features composites |
| v2.0 | - | Architecture 3 tables séparées |
| v1.0 | - | Table unique dénormalisée |

**Architecture v3.0** :
- ✅ Ajout table `market_snapshot_m15` avec foreign keys
- ✅ 7 features composites calculées (alignement, régimes, scores)
- ✅ Pas de duplication des données sources
- ✅ Validation 4 tables + Discord notification
