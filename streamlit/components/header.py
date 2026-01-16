"""
Header - Titre et timestamp de la page
"""

import streamlit as st
from datetime import datetime


def render_header():
    """Affiche le header principal de la page"""
    st.title("📊 OrionTrader - Dashboard de Trading")
    st.caption(f"Dernière mise à jour: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
