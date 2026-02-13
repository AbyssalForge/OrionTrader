"""
Sidebar - Barre latérale avec statuts et filtres
"""

import streamlit as st
from utils.database import test_database_connection
from utils.api_client import get_health_status


def render_sidebar():
    with st.sidebar:
        st.title("Configuration")

        st.subheader("Connexions")

        if test_database_connection():
            st.success("Base de données : connectée")
        else:
            st.error("Base de données : déconnectée")

        try:
            health = get_health_status()
            if health.get("status") == "ok":
                st.success("API : disponible")
            else:
                st.warning("API : indisponible")
        except Exception:
            st.error("API : erreur de connexion")

        st.divider()

        st.subheader("Période")

        time_range = st.selectbox(
            "Plage temporelle",
            ["Dernière heure", "Dernières 4h", "Aujourd'hui", "Derniers 7 jours", "Dernier mois"],
            index=1
        )

        st.divider()

        st.subheader("Rafraîchissement")

        auto_refresh = st.checkbox("Auto-refresh", value=False)
        refresh_interval = 60

        if auto_refresh:
            refresh_interval = st.slider(
                "Intervalle (secondes)",
                min_value=10,
                max_value=300,
                value=60,
                step=10
            )

        st.divider()
        st.caption("OrionTrader v3.0")

    return {
        "time_range": time_range,
        "auto_refresh": auto_refresh,
        "refresh_interval": refresh_interval
    }
