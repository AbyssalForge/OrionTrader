# OrionTrader

Plateforme MLOps de trading algorithmique sur la paire EUR/USD. Architecture microservices complète : collecte de données, feature engineering, entraînement et déploiement de modèles ML, API REST, dashboard et monitoring.

---

## Architecture générale

```
Windows Host (MetaTrader 5)
        │
        │ Pyro5 RPC (port 5000/9001)
        ▼
┌───────────────────────────────────────────────────────┐
│                  Docker Compose                       │
│                                                       │
│  Airflow (8080) ──► PostgreSQL (5432) ◄── FastAPI (8000) │
│      │                    │                    │      │
│  ETL Pipelines      5 tables trading      API REST   │
│  CD Model           + auth               ML Predict  │
│      │                    │                    │      │
│  MLflow (5000)      Streamlit (8502)   Monitoring     │
│  Experiments        Dashboard          Prometheus     │
│  Model Registry                        Grafana        │
│                                                       │
│  Vault (8200)  ──  Secrets & API keys                 │
└───────────────────────────────────────────────────────┘
```

---

## Prérequis

- Docker Desktop
- MetaTrader 5 installé sur Windows (pour la collecte de données live)
- Python 3.11+ (pour le serveur Pyro5 local)

---

## Démarrage rapide

### 1. Configuration

```bash
cp .env.example .env
# Remplir les variables dans .env
```

### 2. Lancer les services Docker

```bash
docker-compose up -d
```

### 3. Connecter MetaTrader 5 aux conteneurs Docker

Le serveur Pyro5 expose les données MT5 (tournant sur Windows) aux conteneurs via RPC.
Lancer dans cet ordre depuis le dossier `metatrader/server/` :

```bash
# Terminal 1 — Nameserver Pyro5 (doit démarrer en premier)
python -m Pyro5.nameserver -n 127.0.0.1 -p 9001

# Terminal 2 — Serveur RPC MetaTrader5
python server.py
```

Le serveur s'enregistre sous le nom `forex.server` dans le nameserver.
Les conteneurs Airflow/FastAPI accèdent aux données via `host.docker.internal`.

---

## Services

| Service | URL | Credentials |
|---|---|---|
| Airflow | http://localhost:8080 | admin / admin |
| FastAPI (Swagger) | http://localhost:8000/docs | token dans Vault |
| Streamlit | http://localhost:8502 | — |
| MLflow | http://localhost:5000 | — |
| Grafana | http://localhost:3000 | admin / admin |
| Prometheus | http://localhost:9090 | — |
| PgAdmin | http://localhost:5050 | admin@admin.com / admin |
| Vault | http://localhost:8200 | token: orion-root-token |
| Marimo | http://localhost:2718 | — |

---

## Pipelines Airflow

Trois DAGs principaux :

**`etl_forex_pipeline`** — ETL quotidien (18h UTC)
- Extract : MT5 M15 + Yahoo Finance + Eurostat
- Transform : feature engineering (100+ features)
- Load : PostgreSQL + market snapshots
- Validation : qualité des données + notification Discord

**`cd_model_pipeline`** — CD modèle (22h UTC, après ETL)
- Validation des métriques du candidat vs seuils
- Test d'inférence sur données holdout
- Packaging en "Staging" dans MLflow Registry
- Déploiement en alias "production"

**`wikipedia_scraping_pipeline`** — Manuel
- Scraping CAC 40, S&P 500, NASDAQ 100, Dow Jones
- Référentiel tickers → secteurs

---

## Modèle ML

**Classification** (LightGBM)

On fournit des données de marché au modèle, qui retourne une décision parmi trois classes :

- `BUY` — prendre une position longue
- `SELL` — prendre une position courte
- `HOLD` — ne rien faire

Le modèle est entraîné sur des features issues des données MT5 M15, Yahoo Finance et Eurostat.

---

## Base de données

5 tables principales dans `trading_data` :

| Table | Source | Fréquence |
|---|---|---|
| `mt5_eurusd_m15` | MetaTrader 5 | 15 minutes |
| `yahoo_finance_daily` | Yahoo Finance | Quotidien |
| `documents_macro` | Eurostat | Hebdomadaire |
| `market_snapshot_m15` | Calculé (Bronze+Silver+Gold) | 15 minutes |
| `wikipedia_indices` | Wikipedia | Manuel |

---

## Structure du projet

```
OrionTrader/
├── airflow/
│   ├── dags/               # Pipelines ETL + CD
│   ├── models/             # ORM SQLAlchemy (tables)
│   ├── services/           # Bronze / Silver / Gold / Validation
│   ├── clients/            # MT5, Yahoo, Eurostat, Vault
│   └── utils/
├── fastapi/
│   └── app/
│       ├── routes/         # auth, market, data, signals, model, monitoring
│       ├── core/           # database, auth, vault, metrics
│       └── schemas/        # Pydantic models
├── streamlit/
│   ├── pages/              # Wikipedia_Data, ML_Model, Analytics
│   ├── components/         # header, sidebar, tabs
│   └── utils/              # api_client, database, vault
├── metatrader/
│   └── server/
│       ├── server.py       # Serveur Pyro5 RPC (Windows)
│       └── utils/          # data_loader, vault_helper
├── marimo/
│   └── notebooks/          # train_classification.py
├── mlflow/                 # Artifacts ML
├── prometheus/             # prometheus.yml
├── grafana/                # Dashboards JSON
├── nginx/                  # Config SSL prod
├── vault/                  # Config HashiCorp Vault
├── docker-init/            # Scripts init conteneurs
├── scripts/
│   └── promote_model.py    # Promotion manuelle staging → prod
├── tests/                  # pytest
├── docker-compose.yml      # Dev local
├── docker-compose.prod.yml # Production OVH VPS
└── .env.example
```

---

## API FastAPI — Endpoints principaux

| Route | Description |
|---|---|
| `POST /model/predict` | Prédiction SHORT/NEUTRAL/LONG |
| `GET /market/latest` | Dernier snapshot marché |
| `GET /data/features/latest` | Features MT5 + Yahoo + Macro |
| `GET /signals/high-confidence` | Signaux filtrés haute confiance |
| `GET /monitoring/metrics` | Métriques Prometheus |
| `POST /auth/token` | Authentification |

Documentation interactive : http://localhost:8000/docs

---

## Déploiement production (OVH VPS)

Le fichier `docker-compose.prod.yml` sépare les services en deux réseaux :

- **Réseau VPN** (WireGuard via wg-easy) : postgres, pgadmin, mlflow, marimo
- **Internet** (via Nginx SSL) : fastapi (8001), streamlit (8501)

```bash
docker-compose -f docker-compose.prod.yml up -d
```

CI/CD via GitHub Actions :
- **CI** (`ci-tests.yml`) : tests + linting sur push/PR
- **CD** (`cd-deploy.yml`) : build Docker → push GHCR → SSH deploy OVH

---

## Secrets

Tous les secrets sont gérés via HashiCorp Vault (mount `orionTrader`) :

- Clés API (Yahoo Finance, Eurostat)
- Credentials MT5
- Webhook Discord (notifications pipeline)
- Tokens FastAPI

Interface Vault : http://localhost:8200/ui — token : `orion-root-token`

---

## Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v --cov=airflow --cov=fastapi
```
