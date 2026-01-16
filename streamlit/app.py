"""
OrionTrader - Dashboard Streamlit
Visualisation des données de trading en temps réel

Architecture modulaire:
- config/page_config.py : Configuration de la page
- components/sidebar.py : Barre latérale
- components/header.py : Titre et timestamp
- components/metrics.py : Métriques clés
- components/tabs/*.py : Onglets du dashboard
"""

import streamlit as st

# Configuration de la page (DOIT être en premier)
from config.page_config import configure_page
configure_page()

# Composants
from components.sidebar import render_sidebar
from components.header import render_header
from components.metrics import render_metrics_row

# Tabs
from components.tabs.tab_prices import render_prices_tab
from components.tabs.tab_regimes import render_regimes_tab
from components.tabs.tab_analysis import render_analysis_tab
from components.tabs.tab_raw_data import render_raw_data_tab


# ============================================================================
# SIDEBAR
# ============================================================================

config = render_sidebar()


# ============================================================================
# HEADER
# ============================================================================

render_header()


# ============================================================================
# METRICS ROW
# ============================================================================

render_metrics_row()

st.divider()


# ============================================================================
# TABS - DIFFÉRENTES VUES
# ============================================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Prix & Signaux",
    "📊 Régimes",
    "🔍 Analyse",
    "📋 Données brutes"
])

with tab1:
    render_prices_tab()

with tab2:
    render_regimes_tab()

with tab3:
    render_analysis_tab()

with tab4:
    render_raw_data_tab()


# ============================================================================
# AUTO-REFRESH
# ============================================================================

if config.get("auto_refresh", False):
    import time
    time.sleep(config.get("refresh_interval", 60))
    st.rerun()
