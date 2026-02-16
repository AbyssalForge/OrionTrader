"""
Configuration de la page Streamlit
"""

import streamlit as st


def configure_page():
    """Configure les paramètres de la page Streamlit"""
    st.set_page_config(
        page_title="OrionTrader Dashboard",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded"
    )
