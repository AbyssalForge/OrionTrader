"""
Header - Titre et timestamp de la page
"""

import streamlit as st
from datetime import datetime


def render_header():
    st.title("OrionTrader - Dashboard de trading")
    st.caption(f"Mise à jour : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
