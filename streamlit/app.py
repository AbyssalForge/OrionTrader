"""
OrionTrader - Dashboard principal
"""

import streamlit as st
from datetime import datetime

st.set_page_config(
    page_title="OrionTrader",
    layout="wide",
    initial_sidebar_state="expanded"
)

with st.sidebar:
    st.markdown("""
    ### Navigation

    - **Wikipedia Data** : Données d'indices boursiers
    - **ML Model** : Prédictions EUR/USD
    - **Analytics** : Analyse des marchés
    """)

    st.divider()
    st.caption(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


st.title("OrionTrader")
st.markdown("Plateforme d'analyse et de prédiction des marchés financiers.")

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.info("""
    ### Données de marché

    Consultez les données d'indices boursiers (CAC 40, S&P 500, NASDAQ 100, Dow Jones) :
    entreprises, secteurs, pays et appartenance aux indices.
    """)

with col2:
    st.success("""
    ### Prédiction EUR/USD

    Entrez les données OHLCV d'une bougie EUR/USD pour obtenir un signal
    directionnel (LONG / NEUTRAL / SHORT) avec niveau de confiance.
    """)

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Indices suivis", "4", help="CAC 40, S&P 500, NASDAQ 100, Dow Jones")

with col2:
    st.metric("Entreprises", "~700", help="Nombre d'entreprises dans la base")

with col3:
    st.metric("Marché couvert", "EUR/USD", help="Paire de devises principale")

st.divider()

st.caption("Disclaimer : Cette application est fournie à titre informatif. Les prédictions ne constituent pas des conseils financiers.")
