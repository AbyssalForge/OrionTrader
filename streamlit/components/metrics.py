"""
Metrics Row - Métriques clés du marché en temps réel
"""

import streamlit as st
from utils.api_client import get_market_snapshot


def render_metrics_row():
    col1, col2, col3, col4 = st.columns(4)

    try:
        latest = get_market_snapshot()

        with col1:
            confidence = latest.get('signal_confidence_score', 0)
            st.metric("Confiance du signal", f"{confidence:.2f}")

        with col2:
            regime = latest.get('regime_composite', 'neutral')
            st.metric("Régime de marché", regime.upper())

        with col3:
            vol_regime = latest.get('volatility_regime', 'normal')
            st.metric("Volatilité", vol_regime.upper())

        with col4:
            event_active = latest.get('event_window_active', False)
            st.metric("Fenêtre d'événement", "Actif" if event_active else "Inactif")

    except Exception as e:
        st.error(f"Erreur lors de la récupération des données : {e}")
