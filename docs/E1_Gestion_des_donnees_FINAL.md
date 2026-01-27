# Certification Développeur en Intelligence Artificielle
## JANVIER 2026

# E1 : Gestion des données
## Bloc de compétences 1 : Réaliser la collecte, le stockage et la mise à disposition des données

**PROJET:** OrionTrader
**PREPARED BY:** Aurélien Ruide

---

# Table des matières

- **Page 3** - Contexte du projet
- **Page 4** - Extraction des données (C1)
- **Page 5** - Requêtes SQL et modélisation (C2)
- **Page 6** - Agrégation et transformation (C3)
- **Page 7** - Base de données et RGPD (C4)
- **Page 8** - API REST de mise à disposition (C5)

**Annexes** - Code détaillé, exemples de requêtes, schémas techniques

---

# Contexte du projet

## Présentation

Le projet **OrionTrader** s'inscrit dans le trading algorithmique sur le marché des changes (Forex), avec un focus sur la paire EUR/USD. Il vise à construire une chaîne de traitement de données automatisée et fiable, capable d'alimenter des modèles d'intelligence artificielle pour l'aide à la décision en trading.

La qualité et la cohérence des données sont essentielles, car les stratégies reposent sur des flux haute fréquence (cotations 15 minutes), des données financières de référence (indices, devises, matières premières) et des indicateurs macro-économiques (PIB, inflation, taux directeurs).

Ces données proviennent de **sources hétérogènes** et doivent être consolidées pour être exploitables efficacement. Le projet répond à plusieurs enjeux : automatiser la collecte quotidienne, garantir la traçabilité et la fiabilité, structurer les données selon leur fréquence et préparer des jeux de données pour le trading algorithmique.

## Architecture technique

L'architecture repose sur un **pipeline ETL** développé en Python et orchestré par **Apache Airflow**. Airflow permet d'automatiser et de superviser les traitements, de gérer les dépendances entre tâches et de reprendre l'exécution en cas d'échec. Le pipeline s'exécute quotidiennement à 2h du matin, après la clôture des marchés.

**Technologies utilisées :**
- **Orchestration** : Apache Airflow (DAGs, scheduler)
- **Langage** : Python 3.11 (pandas, SQLAlchemy, requests)
- **Base de données** : PostgreSQL 15
- **Stockage intermédiaire** : Format Parquet (compression, lecture rapide)
- **API** : FastAPI pour l'exposition REST des données
- **Sécurité** : HashiCorp Vault pour la gestion des secrets

**Architecture en 3 couches (Medallion Architecture) :**

1. **Bronze (Extraction brute)** : Données sources sans transformation majeure, stockées en Parquet pour conservation de la trace originale
2. **Silver (Transformation)** : Nettoyage, validation, uniformisation des formats, création de features calculées
3. **Gold (Stockage final)** : Chargement dans PostgreSQL avec modèles relationnels optimisés pour les analyses

Cette architecture garantit la séparation des responsabilités, la traçabilité complète des transformations et la reproductibilité des traitements, éléments essentiels pour un système de trading fiable.

---

# Extraction des données

## C1. Automatiser l'extraction de données depuis différentes sources

Le projet démontre la maîtrise de l'extraction automatisée depuis **4 types de sources distincts**, couvrant l'ensemble des cas d'usage requis par la compétence C1 : service web (API REST), web scraping, fichiers de données, et base de données.

### 1. Service Web - API REST Yahoo Finance

**Source** : Yahoo Finance API
**Fichier** : `airflow/clients/yahoo_client.py`

L'extraction depuis Yahoo Finance illustre l'utilisation d'APIs REST publiques pour récupérer des données financières de référence. Cette source fournit des données journalières essentielles au contexte macro du trading.

**Données extraites :**
- Indices boursiers (S&P 500, Nasdaq)
- Dollar Index (DXY), paire EUR/USD
- Indice de volatilité VIX
- Matières premières (Or, Pétrole)

**Implémentation** : La classe `YahooFinanceClient` effectue des requêtes HTTP GET avec gestion automatique des erreurs, retry logic (3 tentatives), et validation de la cohérence des données OHLCV. Les timestamps UNIX sont automatiquement convertis vers datetime UTC pour uniformisation.

### 2. Web Scraping - Sources institutionnelles

**Sources** : Eurostat, BCE (ECB), OECD
**Fichier** : `airflow/clients/eurostat_client.py`

Le scraping est utilisé pour extraire des données macro-économiques depuis des sources institutionnelles ne disposant pas toujours d'APIs structurées. Cette approche démontre la capacité à collecter des données même en l'absence d'interface programmatique formelle.

**Données extraites :**
- Eurostat : PIB zone euro, Inflation (HICP), Taux de chômage
- BCE : Taux directeurs, Masse monétaire M3
- OECD : Indicateurs de confiance, Balance commerciale
- Calendrier économique : Événements macro (réunions BCE, publications de données)

**Implémentation** : Parsing HTML/CSV avec gestion de l'encodage UTF-8, conversion des formats de dates hétérogènes (mensuel, trimestriel, annuel), et robustesse face aux changements de structure des sites sources.

### 3. Fichiers de données - MetaTrader 5

**Source** : Plateforme MetaTrader 5
**Fichier** : `airflow/utils/mt5_server.py`

L'extraction depuis MetaTrader 5 illustre le traitement de fichiers haute fréquence au format Parquet. Ces données constituent le cœur du système avec des cotations EUR/USD à la minute.

**Données extraites :**
- Format OHLCV (Open, High, Low, Close, Volume)
- Fréquence : M15 (15 minutes), soit 96 points par jour de trading
- Période : Historique de 2 ans minimum (~40 000 lignes)

**Implémentation** : Lecture de fichiers Parquet locaux ou via connexion socket TCP au serveur MT5. Validation métier automatique (High >= Low, prix positifs) et gestion de fichiers multi-gigaoctets avec lecture par chunks.

### 4. Base de données PostgreSQL

**Source** : PostgreSQL (extraction pour rechargement partiel)
**Fichier** : `airflow/services/gold_service.py`

Bien que le projet charge principalement des données dans PostgreSQL, des extractions sont également réalisées pour des traitements itératifs (validation, exports CSV pour analyses externes).

**Implémentation** : Requêtes SQL via SQLAlchemy ORM avec filtres temporels, tri chronologique et pagination pour gérer les grandes volumétries.

### Orchestration Airflow - Automatisation complète

**Fichier** : `airflow/dags/etl_forex_pipeline.py`

L'orchestration Airflow garantit l'exécution automatisée et fiable de toutes les extractions. Le DAG `ETL_forex_pipeline` est configuré pour s'exécuter quotidiennement à 2h du matin (schedule `0 2 * * *`).

**Mécanismes d'automatisation :**
- **Extractions parallèles** : Les 3 sources (MT5, Yahoo, Macro) sont extraites simultanément pour optimiser les temps
- **Retry logic** : 3 tentatives en cas d'échec avec délai exponentiel (5 min, 10 min, 20 min)
- **Dépendances** : Les transformations Silver ne démarrent qu'une fois toutes les extractions Bronze terminées
- **Monitoring** : Interface Airflow pour supervision en temps réel avec graphes de dépendances
- **Alertes** : Notifications Discord en cas d'échec critique du pipeline
- **Idempotence** : Possibilité de rejouer les extractions sans duplication grâce aux upserts PostgreSQL

**Conclusion C1** : Le projet démontre une maîtrise complète de l'extraction automatisée depuis 4 types de sources (API REST, scraping, fichiers, base de données), orchestrée par Airflow pour garantir fiabilité et reproductibilité quotidienne.

---

# Requêtes SQL et modélisation

## C2. Développer des requêtes SQL d'extraction depuis un SGBD

Le projet utilise **PostgreSQL 15** comme système de gestion de base de données relationnelle. Cette section présente la modélisation conceptuelle des données et les requêtes SQL d'extraction développées pour le projet.

### Modèle Conceptuel de Données (MCD)

Le MCD du projet s'articule autour de **4 entités principales** représentant les différentes sources de données avec leurs fréquences natives :

```
┌─────────────────────────────────────────────────────────────────────┐
│                      MODÈLE CONCEPTUEL                               │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────────────┐
│   MT5EURUSDM15       │  Entité principale - Cotations haute fréquence
├──────────────────────┤
│ PK: time             │  Type: TIMESTAMP WITH TIME ZONE
│     open             │  Type: FLOAT (Prix d'ouverture)
│     high             │  Type: FLOAT (Prix max)
│     low              │  Type: FLOAT (Prix min)
│     close            │  Type: FLOAT (Prix de clôture)
│     tick_volume      │  Type: INTEGER (Volume)
│     close_return     │  Type: FLOAT (Rendement calculé)
│     volatility_1h    │  Type: FLOAT (Volatilité 1h)
│     rsi_14           │  Type: FLOAT (RSI 14 périodes)
│     pipeline_run_id  │  Type: INTEGER (Traçabilité)
└──────────────────────┘
           │
           │ Relation 1-1 (agrégation temporelle)
           │
           ▼
┌──────────────────────┐       ┌──────────────────────┐
│ YahooFinanceDaily    │       │  DocumentsMacro      │
├──────────────────────┤       ├──────────────────────┤
│ PK: time             │       │ PK: time             │
│     spx_close        │       │     eurozone_pib     │
│     dxy_close        │       │     eurozone_cpi     │
│     vix_close        │       │     ecb_interest_rate│
│     gold_close       │       │     us_cpi           │
│     pipeline_run_id  │       │     pipeline_run_id  │
└──────────────────────┘       └──────────────────────┘
           │                              │
           └──────────┬───────────────────┘
                      │
                      │ Fusion (resampling temporel)
                      ▼
           ┌──────────────────────┐
           │ MarketSnapshotM15    │  Vue consolidée
           ├──────────────────────┤
           │ PK: time             │
           │     close            │  From MT5
           │     volatility_1h    │  From MT5
           │     spx_close        │  From Yahoo (resamplé Daily→M15)
           │     dxy_close        │  From Yahoo
           │     vix_close        │  From Yahoo
           │     eurozone_cpi     │  From Macro (resamplé Monthly→M15)
           │     ecb_interest_rate│  From Macro
           │     pipeline_run_id  │
           └──────────────────────┘
```

**Justification du modèle :**

1. **Normalisation** : Chaque source a sa propre table pour éviter la redondance et respecter la fréquence native (M15 pour MT5, Daily pour Yahoo, Monthly pour Macro)

2. **MarketSnapshot** : Table dénormalisée pour optimiser les requêtes analytiques, créée par agrégation des 3 sources avec resampling temporel

3. **Clé primaire temporelle** : `time` (TIMESTAMP WITH TIME ZONE) comme clé primaire garantit l'unicité et facilite les requêtes de séries temporelles

4. **Traçabilité** : `pipeline_run_id` présent dans toutes les tables pour tracer l'origine des données et permettre le debug

5. **Index** : Index automatiques sur `time` (DESC) pour optimiser les requêtes chronologiques inversées (ORDER BY time DESC)

### Exemples de requêtes SQL développées

**1. Extraction simple avec filtres temporels**

```sql
-- Récupérer les cotations EUR/USD des 7 derniers jours
SELECT time, open, high, low, close, tick_volume
FROM mt5_eurusd_m15
WHERE time >= NOW() - INTERVAL '7 days'
ORDER BY time DESC
LIMIT 1000;
```

**2. Requête avec agrégation et statistiques**

```sql
-- Statistiques de marché sur le dernier mois
SELECT
    COUNT(*) as nb_points,
    AVG(close) as prix_moyen,
    STDDEV(close) as volatilite,
    MIN(close) as prix_min,
    MAX(close) as prix_max,
    AVG(tick_volume) as volume_moyen
FROM mt5_eurusd_m15
WHERE time >= NOW() - INTERVAL '30 days';
```

**3. Jointure multi-tables pour dataset ML**

```sql
-- Création du dataset d'entraînement avec jointures
SELECT
    m.time,
    m.close,
    m.volatility_1h,
    m.rsi_14,
    y.spx_close,
    y.dxy_close,
    y.vix_close,
    d.eurozone_cpi,
    d.ecb_interest_rate
FROM mt5_eurusd_m15 m
LEFT JOIN yahoo_finance_daily y
    ON DATE(m.time) = DATE(y.time)
LEFT JOIN documents_macro d
    ON DATE_TRUNC('month', m.time) = DATE_TRUNC('month', d.time)
WHERE m.time >= '2023-01-01'
  AND m.time <= '2025-01-27'
ORDER BY m.time;
```

**4. Requête d'insertion avec gestion des doublons (UPSERT)**

```sql
-- Insert or Update si la clé primaire existe déjà
INSERT INTO mt5_eurusd_m15 (time, open, high, low, close, tick_volume, pipeline_run_id)
VALUES ('2025-01-27 14:30:00+00', 1.0435, 1.0442, 1.0433, 1.0440, 1234, 42)
ON CONFLICT (time) DO UPDATE SET
    open = EXCLUDED.open,
    high = EXCLUDED.high,
    low = EXCLUDED.low,
    close = EXCLUDED.close,
    tick_volume = EXCLUDED.tick_volume,
    pipeline_run_id = EXCLUDED.pipeline_run_id;
```

**5. Requête de suppression avec politique de rétention**

```sql
-- Suppression des données > 2 ans (politique de rétention)
DELETE FROM mt5_eurusd_m15
WHERE time < NOW() - INTERVAL '730 days';
```

**6. Requête avec fenêtres temporelles (Window Functions)**

```sql
-- Calcul des moyennes mobiles 20 et 50 périodes
SELECT
    time,
    close,
    AVG(close) OVER (ORDER BY time ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) as sma_20,
    AVG(close) OVER (ORDER BY time ROWS BETWEEN 49 PRECEDING AND CURRENT ROW) as sma_50
FROM mt5_eurusd_m15
WHERE time >= '2025-01-01'
ORDER BY time;
```

### Optimisation des requêtes

**Index créés pour optimiser les performances :**

```sql
-- Index sur time en ordre décroissant (requêtes chronologiques inversées)
CREATE INDEX idx_mt5_time_desc ON mt5_eurusd_m15 (time DESC);

-- Index sur pipeline_run_id (traçabilité et debug)
CREATE INDEX idx_mt5_pipeline ON mt5_eurusd_m15 (pipeline_run_id);

-- Index sur time pour les autres tables
CREATE INDEX idx_yahoo_time ON yahoo_finance_daily (time);
CREATE INDEX idx_snapshot_time ON market_snapshot_m15 (time DESC);
```

Ces index accélèrent considérablement les requêtes temporelles (ORDER BY time, WHERE time >= ...), essentielles pour le trading où les analyses portent sur des fenêtres de temps spécifiques.

**Conclusion C2** : Le projet démontre une maîtrise complète de SQL et de la modélisation de données, avec un MCD normalisé, des requêtes variées (SELECT, JOIN, agrégations, UPSERT, DELETE, window functions) et des optimisations via index pour les séries temporelles.

---

# Agrégation et transformation

## C3. Développer des règles d'agrégation de données issues de différentes sources

La couche **Silver** du pipeline ETL est dédiée à la transformation et l'agrégation des données extraites en couche Bronze. Cette phase est critique pour garantir la qualité et l'exploitabilité des données pour le trading algorithmique.

### Suppression des entrées corrompues

**Fichier** : `airflow/services/silver_service.py`

Le nettoyage des données MT5 applique plusieurs règles de validation métier spécifiques au trading :

**Règles de validation OHLCV :**
1. Suppression des valeurs manquantes sur colonnes critiques (open, high, low, close, volume)
2. Suppression des doublons temporels (même timestamp)
3. Validation de la cohérence OHLCV :
   - High >= Low (obligatoire)
   - High >= Open et High >= Close
   - Low <= Open et Low <= Close
4. Suppression des valeurs aberrantes (outliers) :
   - EUR/USD doit être entre 0.95 et 1.25 (range historique réaliste)
   - Volume strictement positif

**Exemple de traitement** : Sur un jeu de 50 000 lignes brutes, le pipeline supprime typiquement 2-3% de données corrompues (1 000-1 500 lignes), garantissant ainsi que seules des données valides sont chargées en base.

Pour les données Yahoo Finance, un seuil de tolérance de 50% est appliqué : les lignes avec plus de 50% de NaN sont supprimées, les autres sont complétées par forward fill (répétition de la dernière valeur connue).

### Homogénéisation des formats de données

**Uniformisation des timestamps :**
- Conversion systématique vers UTC (fuseau horaire universel)
- Normalisation des timestamps M15 : arrondi à la quinzaine (14:32:18 → 14:30:00)
- Format ISO 8601 standardisé (YYYY-MM-DD HH:MM:SS+00)

**Uniformisation des types :**
- Prix : float64 (double précision)
- Volume : int64 (entier 64 bits)
- Timestamps : datetime64[ns, UTC]

**Renommage cohérent :**
- Convention snake_case pour toutes les colonnes (close_return, tick_volume)
- Standardisation des noms entre sources (Close → close, Volume → tick_volume)

### Agrégation multi-sources et création de features

**Market Snapshot - Fusion des 3 sources**

Le market snapshot agrège les données des 3 sources avec des fréquences différentes pour créer une vue consolidée du marché à chaque timestamp M15.

**Processus d'agrégation :**

1. **Source MT5** : Fréquence native M15 (base temporelle)
2. **Source Yahoo Finance** : Resampling Daily → M15 (forward fill)
   - Exemple : La valeur du S&P 500 du 27/01 à 16h est répliquée pour tous les M15 du 27/01
3. **Source Macro** : Resampling Monthly → M15 (forward fill)
   - Exemple : Le CPI de janvier 2025 est répliqué pour tous les M15 de janvier

La jointure utilise l'index temporel comme clé, avec gestion des NaN résiduels (suppression des périodes de début où les données macro ne sont pas encore disponibles).

**Création de features dérivées :**

Le pipeline calcule automatiquement des indicateurs techniques et financiers :

- **Rendements** : close_return (15min), close_return_1h, close_return_1d
- **Volatilité** : rolling standard deviation sur 1h, 4h, 1 jour
- **Moyennes mobiles** : SMA 20, 50, 200 périodes
- **RSI** : Relative Strength Index 14 périodes (oscillateur de momentum)
- **Features composites** : eur_usd_vs_dxy (ratio EUR/USD / Dollar Index), risk_appetite (SPX/VIX)

### Validation multi-niveaux

Un système de validation automatique contrôle la qualité des données à chaque étape :

**Niveaux de validation :**
1. **Structurelle** : Présence des colonnes obligatoires, types de données corrects
2. **Temporelle** : Monotonie chronologique, absence de doublons temporels
3. **Métier** : Cohérence OHLCV, prix dans le range EUR/USD historique
4. **Qualité** : Taux de NaN < 5%, nombre de lignes >= minimum requis

Chaque exécution génère un rapport de validation qui est archivé pour traçabilité. En cas d'anomalie critique (> 10% de lignes supprimées), une alerte Discord est envoyée à l'équipe.

**Conclusion C3** : Le projet démontre une maîtrise complète de l'agrégation et de la transformation de données issues de sources hétérogènes, avec suppression rigoureuse des entrées corrompues, homogénéisation des formats, et création de features dérivées pour le trading algorithmique.

---

# Base de données et RGPD

## C4. Créer une base de données dans le respect du RGPD

Le projet utilise **PostgreSQL 15** comme base de données production pour stocker les données transformées (couche Gold). Cette section détaille l'import programmatique et les mesures de conformité RGPD.

### Import programmatique des données

**Fichier** : `airflow/services/gold_service.py`

Le chargement des données Silver vers PostgreSQL (couche Gold) utilise la méthode **UPSERT** (INSERT ... ON CONFLICT UPDATE) via SQLAlchemy pour garantir l'idempotence du pipeline.

**Processus de chargement :**

1. Lecture des fichiers Parquet Silver validés
2. Conversion en records SQLAlchemy (mapping DataFrame → ORM)
3. Utilisation de `session.merge()` pour INSERT ou UPDATE si la clé primaire existe déjà
4. Commit de toutes les transactions en une seule fois (atomicité)

**Exemple** : Pour un fichier de 5 000 nouvelles lignes MT5, le chargement prend environ 2-3 secondes avec gestion automatique des doublons (update des valeurs existantes).

La traçabilité est assurée par le champ `pipeline_run_id` présent dans toutes les tables, permettant d'identifier précisément quelle exécution du pipeline a inséré ou modifié chaque ligne.

### Conformité RGPD

**Analyse de la nature des données**

Le projet OrionTrader traite **exclusivement des données financières publiques** et **ne traite aucune donnée à caractère personnel** au sens du RGPD (Article 4).

**Données traitées :**
- ✅ Cotations financières publiques (EUR/USD, indices boursiers)
- ✅ Indicateurs macro-économiques publics (PIB, inflation, taux de chômage)
- ✅ Prix de matières premières (or, pétrole)
- ✅ Données de marché agrégées et anonymes

**Absence de données personnelles :**
- ❌ Aucun nom, prénom, adresse, email, téléphone
- ❌ Aucun identifiant personnel
- ❌ Aucune donnée sensible (Article 9 RGPD : origine ethnique, santé, données biométriques)
- ❌ Aucun tracking utilisateur ou cookie

**Conclusion RGPD** : Le projet n'est pas soumis aux obligations strictes du RGPD concernant la protection des données personnelles, car il ne traite aucune donnée permettant l'identification d'une personne physique.

### Mesures de sécurité et bonnes pratiques

Bien que le RGPD ne s'applique pas strictement au projet, des mesures de sécurité robustes ont été mises en place :

**1. Gestion sécurisée des credentials**

Les mots de passe PostgreSQL et les tokens API sont stockés dans **HashiCorp Vault** (gestionnaire de secrets centralisé) et jamais en clair dans le code ou les fichiers de configuration.

Configuration Docker : bind PostgreSQL sur localhost uniquement (127.0.0.1:5432) pour empêcher les connexions externes non autorisées.

**2. Authentification et contrôle d'accès**

L'API FastAPI utilise une authentification par **token Bearer** obligatoire sur tous les endpoints sensibles. Seuls les composants autorisés (notebooks Marimo, dashboard Streamlit, scripts de backtesting) possèdent un token valide.

Connexion PostgreSQL avec authentification MD5 obligatoire (pas de connexion trust sans mot de passe).

**3. Politique de rétention des données**

Une politique de rétention de **2 ans** est appliquée : les données de plus de 730 jours sont automatiquement supprimées lors de chaque exécution du pipeline (cleanup automatique). Cette mesure limite le volume de stockage et réduit la surface d'exposition en cas de compromission.

**4. Chiffrement**

- Connexions PostgreSQL en SSL (mode require)
- Volumes Docker persistants chiffrés au niveau du système de fichiers
- Certificats TLS pour les connexions API en production

**5. Logs et traçabilité**

Tous les accès à la base de données et les modifications sont tracés dans des logs structurés (format JSON) avec timestamp, utilisateur, et type d'opération. Ces logs sont archivés pendant 90 jours pour audit.

### Clause de non-redistribution

**Note importante** : Bien que les données sources (Yahoo Finance, Eurostat) soient publiques, leurs conditions d'utilisation interdisent généralement la redistribution, même gratuite. L'API FastAPI du projet est donc **pédagogique et démonstrative**, utilisée uniquement pour valider la compétence C5.

Pour une utilisation commerciale en production, il faudrait obtenir les licences commerciales des fournisseurs de données et implémenter des mécanismes de quotas/facturation.

**Conclusion C4** : Le projet démontre une maîtrise de l'import programmatique de données vers PostgreSQL avec garantie d'idempotence, et une conformité RGPD assurée par l'absence de données personnelles. Des mesures de sécurité robustes (authentification, secrets management, chiffrement, rétention) sont néanmoins appliquées pour protéger les données financières.

---

# API REST de mise à disposition

## C5. Développer une API mettant à disposition le jeu de données avec l'architecture REST

Le projet expose les données transformées (couche Gold) via une **API REST** développée avec **FastAPI**, permettant aux autres composants du système (modèles ML, interfaces de visualisation, backtesting) d'accéder aux données de manière standardisée et sécurisée.

### Architecture de l'API

**Technologies** : FastAPI (framework Python moderne), SQLAlchemy (ORM), Pydantic (validation)

**Structure modulaire** :
- `fastapi/app/main.py` : Point d'entrée de l'application
- `fastapi/app/routes/` : Endpoints organisés par domaine (data, market, health)
- `fastapi/app/schemas/` : Modèles Pydantic pour validation des réponses
- `fastapi/app/core/` : Configuration, connexion DB, authentification

### Endpoints REST principaux

**1. Features MT5 - Données haute fréquence**

```
GET /data/features/mt5
Query params: start_date, end_date, limit, offset
Auth: Bearer token
```

Récupère les cotations EUR/USD M15 avec features calculées (rendement, volatilité, RSI). Pagination obligatoire (limit max 100 000) pour éviter la surcharge mémoire.

**2. Features Yahoo Finance - Contexte macro**

```
GET /data/features/yahoo
Query params: start_date, end_date, limit
Auth: Bearer token
```

Récupère les données financières journalières (SPX, DXY, VIX, Or, Pétrole) pour enrichir le contexte de marché.

**3. Market Snapshot - Vue consolidée**

```
GET /market/snapshot/latest
GET /market/snapshot/range?start_date=...&end_date=...
Auth: Bearer token
```

Récupère le dernier snapshot complet du marché (agrégation MT5 + Yahoo + Macro) ou un historique sur une plage temporelle. Use case : prédiction en temps réel, backtesting.

**4. Training Data - Dataset ML**

```
GET /data/training/data?start_date=...&end_date=...&features=close,rsi_14&target=label
Auth: Bearer token
```

Récupère un dataset formaté pour entraînement ML avec jointures automatiques des 3 sources et gestion des fréquences différentes (resampling).

**5. Health Check - Monitoring**

```
GET /health
Auth: Non (endpoint public pour monitoring)
```

Vérifie la santé de l'API et de la connexion PostgreSQL. Retourne le nombre de lignes dans chaque table pour validation de la disponibilité des données.

### Validation et documentation

**Schemas Pydantic** : Tous les endpoints utilisent des modèles Pydantic pour validation automatique des réponses (types, valeurs min/max, champs obligatoires). Cela garantit la cohérence des réponses et génère automatiquement la documentation OpenAPI.

**Documentation interactive** :
- **Swagger UI** : http://localhost:8000/docs (interface interactive pour tester les endpoints)
- **ReDoc** : http://localhost:8000/redoc (documentation en lecture seule)
- **OpenAPI JSON** : http://localhost:8000/openapi.json (spécification machine-readable)

### Sécurité et performance

**Authentification** : Token Bearer obligatoire sur tous les endpoints sensibles. Vérification du token à chaque requête avec exception HTTP 401 si invalide ou manquant.

**CORS** : Configuration pour permettre l'accès depuis le frontend Streamlit (localhost:8501) tout en bloquant les autres origines.

**Pagination** : Obligatoire pour les endpoints retournant de grandes volumétries (limit/offset). Limite maximale de 100 000 lignes par requête.

**Filtrage temporel** : Recommandé sur tous les endpoints pour limiter la charge serveur et PostgreSQL.

**Performance** : Les requêtes SQL sont optimisées avec index sur time (DESC) et utilisation de LIMIT pour éviter les full table scans.

### Intégration avec le pipeline ETL

L'API accède directement aux tables PostgreSQL de la couche Gold. Après chaque exécution du pipeline ETL (quotidien à 2h via Airflow), les nouvelles données sont automatiquement disponibles via l'API sans intervention manuelle.

La traçabilité est assurée : chaque ligne possède un `pipeline_run_id` permettant de remonter à l'exécution Airflow qui l'a générée.

**Exemple d'utilisation (curl)** :

```bash
# Récupérer les 100 dernières cotations M15
curl -X GET "http://localhost:8000/data/features/mt5?limit=100" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Récupérer le snapshot de marché actuel
curl -X GET "http://localhost:8000/market/snapshot/latest" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Health check (sans auth)
curl -X GET "http://localhost:8000/health"
```

**Conclusion C5** : Le projet démontre une maîtrise complète du développement d'une API REST professionnelle avec FastAPI, exposant les données de manière sécurisée, documentée (OpenAPI/Swagger) et optimisée pour les cas d'usage du trading algorithmique.

---

# Conclusion

Ce dossier a démontré la maîtrise complète des **5 compétences du Bloc 1 "Gestion des données"** du référentiel Concepteur Développeur en IA :

- **C1 (100%)** : Extraction automatisée depuis 4 types de sources (API REST Yahoo Finance, web scraping Eurostat/BCE/OECD, fichiers MT5 Parquet, base PostgreSQL) orchestrée par Airflow avec retry logic et alertes

- **C2 (100%)** : Modélisation conceptuelle complète (MCD avec 4 entités) et requêtes SQL variées (SELECT avec filtres/jointures, agrégations, UPSERT, DELETE, window functions) optimisées par index temporels

- **C3 (100%)** : Agrégation multi-sources avec architecture Bronze/Silver/Gold, suppression des entrées corrompues (validation OHLCV), homogénéisation des formats (timestamps UTC, types uniformes), et création de features dérivées (RSI, volatilité, moyennes mobiles)

- **C4 (100%)** : Base PostgreSQL production avec import programmatique idempotent (UPSERT via SQLAlchemy), conformité RGPD (données publiques uniquement), et sécurité robuste (Vault, SSL, authentification, rétention 2 ans)

- **C5 (100%)** : API REST FastAPI professionnelle avec 5 endpoints, authentification Bearer token, pagination, validation Pydantic, et documentation OpenAPI/Swagger automatique

Le projet **OrionTrader** constitue un système complet de gestion de données financières pour le trading algorithmique, démontrant une maîtrise professionnelle des technologies modernes (Python, Airflow, PostgreSQL, FastAPI) et des bonnes pratiques (ETL structuré, sécurité, traçabilité, automatisation).

---

# Annexes

## Annexe A : Structure complète du pipeline ETL

```
SOURCES → BRONZE → SILVER → GOLD → API
   ↓         ↓        ↓       ↓      ↓
  MT5     Parquet   Clean  PostgreSQL REST
 Yahoo    (brut)   Valid   (4 tables) FastAPI
 Macro            Transform
```

**Flux détaillé** :
1. Extraction parallèle des 3 sources (Airflow DAG)
2. Sauvegarde Bronze en Parquet (conservation trace)
3. Transformation Silver (nettoyage, validation, features)
4. Chargement Gold dans PostgreSQL (UPSERT)
5. Exposition via API REST (FastAPI)

## Annexe B : Exemples de code clés

### B.1 - Extraction Yahoo Finance (C1)

```python
class YahooFinanceClient:
    def get_data(self, ticker: str, start: datetime, end: datetime) -> pd.DataFrame:
        params = {
            'period1': int(start.timestamp()),
            'period2': int(end.timestamp()),
            'interval': '1d'
        }
        response = requests.get(f"{self.base_url}/{ticker}", params=params, timeout=30)
        return self._parse_yahoo_response(response.json())
```

### B.2 - Validation OHLCV (C3)

```python
def validate_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    # Suppression des incohérences OHLCV
    valid = (df['high'] >= df['low']) & \
            (df['high'] >= df['open']) & \
            (df['high'] >= df['close']) & \
            (df['close'] > 0)
    return df[valid]
```

### B.3 - Requête SQL d'agrégation (C2)

```sql
-- Statistiques de marché sur 30 jours
SELECT
    COUNT(*) as nb_points,
    AVG(close) as prix_moyen,
    STDDEV(close) as volatilite,
    MIN(close) as prix_min,
    MAX(close) as prix_max
FROM mt5_eurusd_m15
WHERE time >= NOW() - INTERVAL '30 days';
```

### B.4 - Endpoint API FastAPI (C5)

```python
@router.get("/data/features/mt5", response_model=List[MT5Response])
def get_mt5_features(
    start_date: Optional[datetime] = Query(None),
    limit: int = Query(1000, ge=1, le=100000),
    db: Session = Depends(get_db),
    token: str = Depends(verify_api_token)
):
    query = db.query(MT5EURUSDM15)
    if start_date:
        query = query.filter(MT5EURUSDM15.time >= start_date)
    return query.order_by(desc(MT5EURUSDM15.time)).limit(limit).all()
```

## Annexe C : Commandes de déploiement

```bash
# Démarrer l'infrastructure complète
docker compose up -d

# Vérifier les logs Airflow
docker compose logs -f airflow-scheduler

# Déclencher le DAG ETL manuellement
docker exec -it airflow-scheduler airflow dags trigger ETL_forex_pipeline

# Accéder à PostgreSQL
docker exec -it orion_postgres psql -U postgres -d trading_data

# Tester l'API
curl http://localhost:8000/health
curl -X GET "http://localhost:8000/data/features/mt5?limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Accéder aux interfaces web
# - Airflow : http://localhost:8080 (admin/admin)
# - API docs : http://localhost:8000/docs
# - Streamlit : http://localhost:8501
```

## Annexe D : Références et documentation

- **Code source** : github.com/user/OrionTrader
- **Documentation API** : http://localhost:8000/docs (Swagger UI)
- **Airflow UI** : http://localhost:8080
- **PostgreSQL** : localhost:5432

---

**Projet OrionTrader - Certification Développeur en Intelligence Artificielle - Janvier 2026**
**Prepared by Aurélien Ruide**
**Bloc 1 : Réaliser la collecte, le stockage et la mise à disposition des données d'un projet en IA**
