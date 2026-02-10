"""
Sidebar - Barre latérale avec configuration et statuts
"""

import streamlit as st
from utils.database import test_database_connection
from utils.api_client import get_health_status


def render_sidebar():
    """
    Affiche la sidebar avec les connexions et filtres

    Returns:
        dict: Configuration sélectionnée (time_range, auto_refresh, refresh_interval)
    """
    with st.sidebar:
        st.title("⚙️ Configuration")

        st.subheader("🔌 Connexion")

        db_status = test_database_connection()
        if db_status:
            st.success("✅ Database: Connectée")
        else:
            st.error("❌ Database: Déconnectée")

        try:
            health = get_health_status()
            if health.get("status") == "ok":
                st.success("✅ API: Disponible")
                total_rows = sum(health.get('tables', {}).values())
                st.caption(f"Tables: {total_rows:,} lignes")
            else:
                st.warning("⚠️ API: Indisponible")
        except Exception:
            st.error("❌ API: Erreur connexion")

        st.divider()

        st.subheader("📅 Période")

        time_range = st.selectbox(
            "Plage temporelle",
            ["Dernière heure", "Dernières 4h", "Aujourd'hui", "Derniers 7 jours", "Dernier mois"],
            index=1
        )

        st.divider()

        st.subheader("🔄 Rafraîchissement")

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
        st.caption("Streamlit Dashboard")

    return {
        "time_range": time_range,
        "auto_refresh": auto_refresh,
        "refresh_interval": refresh_interval
    }
