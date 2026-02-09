# 📊 OrionTrader - Streamlit Dashboard Simplifié

Dashboard MLOps simplifié pour visualiser les données d'indices boursiers et utiliser le modèle de prédiction.

## 🚀 Fonctionnalités

### 🏠 Page d'accueil
- Vue d'ensemble du projet MLOps
- Statistiques rapides
- Accès rapide aux fonctionnalités
- Documentation intégrée

### 🏦 Wikipedia Data
Visualisation des données d'indices boursiers scrapées depuis Wikipedia.

**Fonctionnalités :**
- 📊 Statistiques par indice, secteur, pays
- 🔍 Filtres multiples (indice, secteur, pays)
- 📈 Visualisations interactives (Plotly)
- 🔎 Recherche par ticker ou entreprise
- 📥 Export CSV
- 🏆 Top entreprises multi-indices

**Indices disponibles :**
- CAC 40 (France)
- S&P 500 (USA)
- NASDAQ 100 (USA)
- Dow Jones (USA)

### 🤖 ML Model
Interface pour utiliser le modèle de prédiction LightGBM.

**Fonctionnalités :**
- 🎯 Prédiction EUR/USD (SHORT/NEUTRAL/LONG)
- 📊 Probabilités des 3 classes
- 📈 Visualisation graphique
- ℹ️ Métriques du modèle
- 💡 Interprétation et recommandations

## 🛠️ Architecture

```
Streamlit Dashboard
  ├─ PostgreSQL : Lecture des données Wikipedia
  └─ FastAPI : Appels API pour prédictions ML
```

## 📦 Structure

```
streamlit/
├── app.py                          # Page d'accueil
├── pages/
│   ├── Wikipedia_Data.py           # Données Wikipedia
│   └── ML_Model.py                 # Modèle ML
├── utils/
│   ├── database.py                 # Connexion PostgreSQL
│   ├── vault_helper.py             # Gestion Vault
│   └── api_client.py               # Client FastAPI
├── requirements.txt                # Dépendances
├── Dockerfile                      # Image Docker
└── README.md                       # Documentation
```

## 🚀 Démarrage

### Via Docker (recommandé)

```bash
# Lancer tout le stack
docker-compose up streamlit

# Accès : http://localhost:8501
```

### En local

```bash
cd streamlit

# Installer dépendances
pip install -r requirements.txt

# Variables d'environnement
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

#### Base de données
```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

#### API FastAPI
```bash
FASTAPI_URL=http://fastapi:8000
FASTAPI_API_TOKEN=your-token
```

#### Vault (optionnel)
```bash
VAULT_ADDR=http://vault:8200
VAULT_TOKEN=your-vault-token
```

## 📊 Utilisation

### Navigation

1. **🏠 Page d'accueil** : Vue d'ensemble
2. **🏦 Wikipedia Data** : Explorer les indices
3. **🤖 ML Model** : Faire des prédictions

### Wikipedia Data

1. Utilisez les filtres (indice, secteur, pays)
2. Recherchez un ticker spécifique
3. Explorez les visualisations
4. Téléchargez en CSV

### ML Model

1. Entrez les prix OHLCV
2. Ajoutez des indicateurs (optionnel)
3. Cliquez sur "Prédire"
4. Analysez les résultats

## 🐛 Débogage

### Logs

```bash
# Logs Streamlit
docker logs -f orion_streamlit

# Logs en temps réel
docker logs -f orion_streamlit --tail 50
```

### Tests

```bash
# Test connexion DB
python -c "from utils.database import test_database_connection; print(test_database_connection())"

# Test API
curl http://localhost:8000/health
curl http://localhost:8000/model/info
```

## 📚 Développement

### Ajouter une page

1. Créer `pages/Ma_Page.py`
2. Configuration :
```python
import streamlit as st

st.set_page_config(
    page_title="Ma Page - OrionTrader",
    page_icon="🎯",
    layout="wide"
)

st.title("🎯 Ma Page")
# Votre code...
```

### Cache des données

```python
@st.cache_data(ttl=300)  # 5 minutes
def load_data():
    # Code...
    return data
```

## 🎨 Personnalisation

### Thème

Modifier `.streamlit/config.toml` :

```toml
[theme]
primaryColor = "#FF4B4B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"
```

## 📝 Notes importantes

1. **Données d'exemple** : Affichées si DB non disponible
2. **API requise** : FastAPI doit être accessible pour le modèle ML
3. **Cache** : Données cachées 5 minutes
4. **Sécurité** : Utiliser Vault ou .env pour credentials

## 🚀 Déploiement Production

```yaml
# docker-compose.yml
services:
  streamlit:
    build: ./streamlit
    ports:
      - "8501:8501"
    environment:
      - POSTGRES_HOST=postgres
      - FASTAPI_URL=http://fastapi:8000
    depends_on:
      - postgres
      - fastapi
```

## 📖 Ressources

- [Streamlit Docs](https://docs.streamlit.io/)
- [Plotly Python](https://plotly.com/python/)
- [SQLAlchemy](https://docs.sqlalchemy.org/)

---

⚠️ **Disclaimer** : Application éducative. Les prédictions ne sont pas des conseils financiers.
