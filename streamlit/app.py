"""
OrionTrader - Dashboard Streamlit Simplifié
Application simple avec données Wikipedia et modèle ML
"""

import streamlit as st
from datetime import datetime

# Configuration de la page (DOIT être en premier)
st.set_page_config(
    page_title="OrionTrader - MLOps Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.image("https://raw.githubusercontent.com/streamlit/streamlit/develop/docs/logos/streamlit-icon.png", width=100)
    st.title("OrionTrader")
    st.caption("MLOps Trading Dashboard")

    st.divider()

    st.markdown("""
    ### 📚 Pages disponibles

    - **🏦 Wikipedia Data**: Données d'indices boursiers scrapées
    - **🤖 ML Model**: Prédictions du modèle LightGBM

    ### ℹ️ Informations
    - **Projet**: E3 - IA & MLOps
    - **Données**: Wikipedia + API Yahoo Finance
    - **Modèle**: LightGBM Classification
    """)

    st.divider()

    # Timestamp
    st.caption(f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ============================================================================
# HEADER
# ============================================================================

st.title("📊 OrionTrader - MLOps Dashboard")
st.markdown("""
Bienvenue sur le dashboard OrionTrader ! Cette application vous permet de :
- 📈 Visualiser les données d'indices boursiers (Wikipedia)
- 🤖 Utiliser le modèle ML pour prédire la direction EUR/USD
""")

st.divider()

# ============================================================================
# MAIN PAGE - QUICK ACCESS
# ============================================================================

st.header("🚀 Accès rapide")

col1, col2 = st.columns(2)

with col1:
    st.info("""
    ### 🏦 Wikipedia Data

    Consultez les données d'indices boursiers scrapées depuis Wikipedia :
    - CAC 40 (France)
    - S&P 500 (USA)
    - NASDAQ 100 (USA)
    - Dow Jones (USA)

    Informations disponibles : ticker, entreprise, secteur, pays, etc.
    """)

with col2:
    st.success("""
    ### 🤖 Modèle ML

    Utilisez le modèle de prédiction LightGBM pour prédire la direction du marché EUR/USD.

    Le modèle utilise :
    - Données OHLCV (EUR/USD)
    - Indicateurs externes (optionnels)
    - Features engineering automatique
    """)

st.divider()

# ============================================================================
# STATS RAPIDES
# ============================================================================

st.header("📊 Statistiques rapides")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="📈 Indices suivis",
        value="4",
        delta="CAC40, S&P500, etc.",
        help="Nombre d'indices boursiers scrapés"
    )

with col2:
    st.metric(
        label="🏢 Entreprises",
        value="~700",
        delta="Unique tickers",
        help="Nombre d'entreprises dans la base"
    )

with col3:
    st.metric(
        label="🤖 Modèle",
        value="LightGBM",
        delta="Production",
        help="Modèle actuellement déployé"
    )

with col4:
    st.metric(
        label="🎯 Accuracy",
        value="~75%",
        delta="Balanced",
        help="Performance du modèle"
    )

st.divider()

# ============================================================================
# INSTRUCTIONS
# ============================================================================

with st.expander("📖 Comment utiliser cette application ?"):
    st.markdown("""
    ### Navigation

    Utilisez la barre latérale de gauche pour naviguer entre les pages :

    1. **🏦 Wikipedia Data** :
       - Explorez les données d'indices boursiers
       - Filtrez par indice, secteur, pays
       - Téléchargez les données

    2. **🤖 ML Model** :
       - Entrez les données OHLCV
       - Ajoutez des indicateurs optionnels
       - Obtenez une prédiction avec les probabilités

    ### Architecture MLOps

    Ce projet implémente une architecture MLOps complète :

    - **Airflow** : Orchestration des pipelines (scraping, transformation)
    - **MLflow** : Tracking des modèles et versioning
    - **FastAPI** : API de prédiction
    - **Streamlit** : Interface utilisateur
    - **PostgreSQL** : Base de données
    - **GitHub Actions** : CI/CD automatisé
    """)

st.divider()

st.caption("⚠️ **Disclaimer**: Cette application est fournie à titre éducatif. Les prédictions ne constituent pas des conseils financiers.")
