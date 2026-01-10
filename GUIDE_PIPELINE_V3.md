# Guide Pipeline ETL v3.0 - OrionTrader

## 🎯 Vue d'Ensemble

Pipeline ETL pour trading forex EUR/USD avec **architecture 3 tables séparées** pour éviter la duplication de données et respecter les fréquences natives.

---

## 📊 Architecture

### 3 Tables Sources

```
┌─────────────────────┐
│  MT5 (M15)          │  70,000 lignes × 17 colonnes = Prix + Microstructure
├─────────────────────┤
│  Yahoo (Daily)      │     500 lignes × 14 colonnes = Indices financiers
├─────────────────────┤
│  Documents (Var)    │      50 lignes ×  9 colonnes = PIB, CPI, Events
└─────────────────────┘
    Total: 70,550 lignes
```

### Pourquoi 3 Tables ?

**Problème v2.0 (1 table):**
- PIB répété 70,000 fois → Duplication massive
- Taille: 150 MB
- Maintenance difficile

**Solution v3.0 (3 tables):**
- Chaque donnée à sa fréquence native
- Pas de duplication
- Taille: 20 MB (**85% d'économie**)

---

## 🔄 Workflow Pipeline

```
1. INIT          → Créer tables BDD
                    ↓
2. EXTRACT       → MT5 + Yahoo + Documents (parallèle)
   (Bronze)         ↓         ↓         ↓
                 .parquet  .parquet  .parquet
                    ↓
3. TRANSFORM     → MT5 + Yahoo + Documents (parallèle)
   (Silver)         ↓         ↓         ↓
              +11 feat  +10 feat   +9 feat
                    ↓
4. LOAD          → 3 tables en BDD (parallèle)
   (Gold)           ↓
                 PostgreSQL
                    ↓
5. VALIDATE      → Vérifier qualité 3 tables
                    ↓
6. NOTIFY        → Discord webhook

Total: 30 features créées
```

---

## 📂 Table 1: MT5 (Microstructure)

**Source:** Serveur MT5 local
**Fréquence:** M15 (15 minutes)
**Lignes:** ~70,000 (2 ans)
**Colonnes:** 17

### Données Brutes (5)
- OHLCV: open, high, low, close, tick_volume

### Features Créées (11)
| Catégorie | Features | Utilité ML |
|-----------|----------|------------|
| **Prix** | close_diff, close_return, high_low_range | Variations |
| **Volatilité** | volatility_1h, volatility_4h | Régime vol |
| **Momentum** | momentum_15m, momentum_1h, momentum_4h | Tendance |
| **Chandelier** | body, upper_shadow, lower_shadow | Analyse bougies |

**Exemple:**
```python
df['close_return'] = df['close'].pct_change()
df['volatility_1h'] = df['close'].pct_change().rolling(4).std()
```

---

## 📈 Table 2: Yahoo Finance (Régime de Marché)

**Source:** Yahoo Finance API (yfinance)
**Fréquence:** Daily (1 jour)
**Lignes:** ~500 (2 ans)
**Colonnes:** 14

### Assets (4)
- SPX (S&P 500), DXY (Dollar Index), VIX (Volatilité), Gold (Or)

### Features Créées (10)
| Asset | Features | Utilité ML |
|-------|----------|------------|
| **SPX** | spx_trend, risk_on | Appétit risque |
| **Gold** | gold_trend, safe_haven | Valeur refuge |
| **DXY** | dxy_trend_1h/4h, dxy_strength | Force dollar |
| **VIX** | vix_level, vix_change, market_stress | Stress marché |

**Exemple:**
```python
df['spx_trend'] = df['spx_close'].pct_change(5)  # Tendance 5 jours
df['risk_on'] = (df['spx_trend'] > 0).astype(int)  # Binaire
```

---

## 🌍 Table 3: Documents (Fondamentaux Macro)

**Sources:** OECD, World Bank, ECB, Investing.com
**Fréquence:** Variable (Annual, Monthly, Ponctuel)
**Lignes:** ~40-50 (2 ans)
**Colonnes:** 9

### Données

| Type | Colonnes | Fréquence |
|------|----------|-----------|
| **PIB** | eurozone_pib, pib_change, pib_growth | Trimestriel/Annuel |
| **CPI** | eurozone_cpi, cpi_change, inflation_pressure | Mensuel |
| **Events** | event_title, event_impact, event_impact_score | Ponctuel |

**Exemple:**
```python
df['pib_change'] = df['eurozone_pib'].pct_change()
df['inflation_pressure'] = (df['cpi_change'] > 0.02).astype(int)
```

**Note:** Chaque ligne n'a que ses colonnes (PIB OU CPI OU Events), les autres sont NULL.

---

## 🔧 Transformations (Silver Layer)

### Principe
Chaque source transformée **indépendamment** (pas de merge).

### Features Multi-Horizon

**Pourquoi plusieurs horizons ?**
- Court terme (15m, 1h): Signaux rapides
- Moyen terme (4h, 5 jours): Tendances établies
- Long terme (mensuel, trimestriel): Contexte macro

**Exemple MT5:**
```python
momentum_15m = close.pct_change(1)   # Immédiat
momentum_1h  = close.pct_change(4)   # 4 × 15min
momentum_4h  = close.pct_change(16)  # 16 × 15min
```

---

## ✅ Validation & Notification

### Validation (3 Critères)

| Table | ✅ OK | ⚠️ Warning | ❌ Erreur |
|-------|------|-----------|----------|
| MT5 | ≥ 1,000 lignes | < 1,000 | 0 lignes |
| Yahoo | ≥ 100 lignes | < 100 | 0 lignes |
| Documents | ≥ 10 lignes | < 10 | 0 lignes |

### Notification Discord

**Message type:**
```
✅ Pipeline ETL EURUSD v3.0 terminé

Statut: ✅ Pipeline validé - Toutes les tables OK
Tables validées: 3/3
Total: 70,550 lignes

📊 Données:
• MT5:        70,000 lignes
• Yahoo:         500 lignes
• Documents:      50 lignes

🎯 Pipeline prêt pour export CSV
```

---

## 🗂️ Structure Fichiers

```
airflow/
├── dags/
│   └── etl_forex_pipeline_v3.py       # Pipeline complet
├── models/
│   ├── MT5EURUSDM15.py                # Table 1
│   ├── YahooFinanceDaily.py           # Table 2
│   └── DocumentsMacro.py              # Table 3
├── services/
│   ├── bronze_service.py              # Extraction
│   ├── silver_service.py              # Transformations
│   ├── gold_service.py                # Load BDD
│   └── validation_service.py          # Validation + Discord
└── utils/
    ├── mt5_server.py                  # MT5 connection
    ├── apis_helper.py                 # Yahoo Finance
    ├── documents_helper.py            # OECD, WB, ECB
    └── db_helper.py                   # PostgreSQL
```

---

## 💡 Décisions Techniques

### 1. Pourquoi 3 Tables au lieu de 1 ?

**Avantages:**
- ✅ Pas de duplication (PIB pas répété 70k fois)
- ✅ Fréquences natives respectées (M15, Daily, Variable)
- ✅ Économie 85% espace (20 MB vs 150 MB)
- ✅ Maintenance plus simple

### 2. Pourquoi Pas de Table Composites ?

**Problème:** Features composites (macro_micro_aligned, euro_strength_bias) toujours à 0.

**Raison:** Trop peu de données PIB (8-10 points), conditions jamais satisfaites.

**Solution:** Calcul à l'export CSV (plus flexible).

### 3. Pourquoi Yahoo Finance au lieu d'Alpha Vantage ?

- ✅ Gratuit, pas de clé API
- ✅ Plus d'assets disponibles (DXY, VIX)
- ✅ Pas de limitations

### 4. Pourquoi OECD/World Bank au lieu d'Eurostat ?

- ✅ Données plus récentes
- ✅ API plus simple
- ✅ Pas de problèmes de période temporelle

---

## 📈 Pour la Soutenance

### Message Clé

> **"Pipeline ETL v3.0 avec 3 tables sources séparées évitant la duplication. Feature engineering créant 30 features depuis 3 sources de données (MT5 M15, Yahoo Daily, Documents Variable). Économie 85% d'espace avec validation automatique et notification Discord."**

### Points Forts

1. **Architecture séparée** → Pas de duplication
2. **30 features ML** → 11 MT5 + 10 Yahoo + 9 Documents
3. **Multi-horizon** → Court, moyen et long terme
4. **3 sources données** → Prix + Indices + Macro
5. **Monitoring auto** → Validation + Discord

### Workflow Simple

```
Extract → Transform → Load → Validate → Notify
(3 sources, parallèle)    (3 tables)
```

### Chiffres Clés

- **70,550 lignes** totales
- **30 features** créées
- **3 sources** de données
- **85% économie** d'espace
- **20 MB** en BDD (vs 150 MB v2.0)

---

## 🚀 Commandes Utiles

### Tester Pipeline
```bash
# Dans Airflow UI
DAG: ETL_forex_pipeline_v3 → Trigger
```

### Vérifier Données
```bash
python test_load_db.py
```

### Export CSV (pour ML)
```python
# Merge 3 tables + calcul composites
df_merged = merge_asof(mt5, yahoo, docs)
df_merged.to_csv('features.csv')
```

---

## 📊 Comparaison Versions

| Critère | v2.0 | v3.0 |
|---------|------|------|
| **Tables** | 1 unifiée | 3 séparées |
| **Duplication** | Oui (PIB 70k fois) | Non |
| **Taille BDD** | 150 MB | 20 MB |
| **Features** | 30 (mélangées) | 30 (séparées) |
| **Maintenance** | Difficile | Simple |
| **Flexibilité** | Faible | Excellente |

**Gagnant:** v3.0 🏆

---

**Version:** v3.0 Finale
**Date:** 2026-01-10
**Statut:** ✅ Prêt pour production
