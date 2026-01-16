# OrionTrader Streamlit Dashboard

Dashboard de visualisation en temps réel pour le projet OrionTrader.

## 🚀 Fonctionnalités

### Pages principales

1. **📈 Prix & Signaux**
   - Graphique chandelier EUR/USD M15
   - Signal confidence score en temps réel
   - Indicateurs de tendance

2. **📊 Régimes**
   - Distribution des régimes de marché (risk_on, risk_off, neutral, volatile)
   - Distribution des régimes de volatilité (low, normal, high)
   - Statistiques sur les dernières 1000 bougies

3. **🔍 Analyse**
   - Opportunités de trading (haute confiance + pas d'event)
   - Alertes de divergence
   - Analyse détaillée des signaux

4. **📋 Données brutes**
   - Table complète des market snapshots
   - Export CSV

### Métriques en temps réel

- **Signal Confidence**: Score de confiance du signal actuel (0.0 - 1.0)
- **Régime de marché**: risk_on 🟢, risk_off 🔴, neutral ⚪, volatile 🟠
- **Volatilité**: Régime de volatilité actuel
- **Event Window**: Indicateur d'event économique à fort impact

## 🛠️ Architecture

### Connexions

```
Streamlit
  ├─ Database (PostgreSQL) : Lecture directe via SQLAlchemy
  │   └─ Tables: mt5_eurusd_m15, yahoo_finance_daily, documents_macro, market_snapshot_m15
  │
  └─ FastAPI : Requêtes via API REST
      └─ Endpoints: /health, /market/latest, /signals/*
```

### Hot-reload

Le volume Docker monte le code en mode lecture/écriture (`rw`), ce qui permet le **hot-reload automatique** :
- Modifiez `app.py` ou tout fichier dans `streamlit/`
- Streamlit détecte les changements et recharge automatiquement
- Pas besoin de redémarrer le conteneur

## 📦 Structure

```
streamlit/
├── .streamlit/
│   └── config.toml          # Configuration Streamlit (thème, port, etc.)
├── utils/
│   ├── __init__.py
│   ├── database.py          # Connexion PostgreSQL via SQLAlchemy
│   └── api_client.py        # Client pour FastAPI
├── app.py                   # Application principale
├── Dockerfile               # Image Docker
├── requirements.txt         # Dépendances Python
└── README.md               # Ce fichier
```

## 🚀 Démarrage

### Via Docker Compose (recommandé)

```bash
# Démarrer tous les services
docker-compose up -d

# Accéder au dashboard
# http://localhost:8501
```

### En local (développement)

```bash
cd streamlit

# Installer les dépendances
pip install -r requirements.txt

# Configurer les variables d'environnement
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=postgres
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=postgres
export FASTAPI_URL=http://localhost:8000

# Lancer Streamlit
streamlit run app.py
```

## 🔧 Configuration

### Variables d'environnement

| Variable | Description | Défaut |
|----------|-------------|--------|
| `POSTGRES_HOST` | Host PostgreSQL | `postgres` |
| `POSTGRES_PORT` | Port PostgreSQL | `5432` |
| `POSTGRES_DB` | Nom de la DB | `postgres` |
| `POSTGRES_USER` | User DB | `postgres` |
| `POSTGRES_PASSWORD` | Password DB | `postgres` |
| `FASTAPI_URL` | URL de l'API FastAPI | `http://fastapi:8000` |
| `VAULT_ADDR` | URL de Vault | `http://vault:8200` |
| `VAULT_TOKEN` | Token Vault | `orion-root-token` |

### Port

Le dashboard Streamlit est accessible sur le **port 8501** :
- Local: http://localhost:8501
- Docker: http://localhost:8501

## 📊 Utilisation

### Navigation

1. **Sidebar gauche** : Configuration et filtres
   - Status de connexion (DB + API)
   - Filtres temporels
   - Auto-refresh

2. **Onglets principaux** :
   - Prix & Signaux : Visualisation des prix et scores
   - Régimes : Distribution des régimes de marché
   - Analyse : Opportunités et alertes
   - Données brutes : Export et consultation

### Auto-refresh

Cochez "Auto-refresh" dans la sidebar pour actualiser automatiquement le dashboard :
- Intervalle configurable : 10-300 secondes
- Défaut : 60 secondes

### Export de données

Dans l'onglet "Données brutes", cliquez sur **"📥 Télécharger CSV"** pour exporter les données au format CSV.

## 🐛 Debug

### Logs

```bash
# Voir les logs Streamlit
docker logs -f orion_streamlit

# Logs en temps réel avec suivi des changements
docker logs -f orion_streamlit --tail 50
```

### Erreurs courantes

**❌ Database: Déconnectée**
- Vérifier que PostgreSQL est démarré : `docker ps | grep postgres`
- Vérifier les credentials dans `.env`
- Vérifier que le secret Vault `Database` a `POSTGRES_HOST: "postgres"`

**❌ API: Erreur connexion**
- Vérifier que FastAPI est démarré : `docker ps | grep fastapi`
- Tester l'API manuellement : `curl http://localhost:8000/health`

**🔄 Hot-reload ne fonctionne pas**
- Vérifier que le volume est bien monté : `docker inspect orion_streamlit | grep Mounts`
- Vérifier `fileWatcherType = "poll"` dans `.streamlit/config.toml`
- Redémarrer le conteneur : `docker restart orion_streamlit`

## 📚 Ressources

- [Documentation Streamlit](https://docs.streamlit.io/)
- [Plotly Python](https://plotly.com/python/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/20/orm/)

## 🎨 Personnalisation

### Thème

Modifiez `.streamlit/config.toml` pour personnaliser le thème :

```toml
[theme]
primaryColor = "#FF4B4B"        # Couleur principale
backgroundColor = "#0E1117"      # Fond de page
secondaryBackgroundColor = "#262730"  # Fond secondaire
textColor = "#FAFAFA"           # Couleur du texte
font = "sans serif"             # Police
```

### Ajout de pages

Créez de nouvelles pages dans `streamlit/pages/` :

```
streamlit/
├── app.py                    # Page principale (🏠 Home)
└── pages/
    ├── 1_📈_Trading.py      # Page trading
    ├── 2_📊_Analytics.py    # Page analytics
    └── 3_⚙️_Settings.py     # Page settings
```

Streamlit détecte automatiquement les fichiers dans `pages/` et les ajoute à la navigation.

## 🔐 Sécurité

⚠️ **Important** : Ce dashboard est configuré pour un environnement de développement local.

Pour la production :
- Activer l'authentification Streamlit
- Utiliser HTTPS avec certificats SSL
- Restreindre les accès réseau
- Sécuriser les variables d'environnement
- Activer les CORS sur FastAPI

## 📝 TODO

- [ ] Ajouter authentification utilisateur
- [ ] Implémenter des alertes temps réel (WebSocket)
- [ ] Ajouter graphiques de corrélation multi-assets
- [ ] Créer page de backtesting
- [ ] Intégration MLflow pour suivi des modèles
- [ ] Export automatique vers Excel avec formatage
