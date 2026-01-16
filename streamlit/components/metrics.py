"""
Metrics Row - Affichage des métriques clés en temps réel
"""

import streamlit as st
from utils.api_client import get_market_snapshot


def render_metrics_row():
    """
    Affiche la ligne de métriques en haut du dashboard

    Métriques affichées:
    - Signal Confidence Score
    - Régime de marché
    - Régime de volatilité
    - Event Window (actif/inactif)
    """
    col1, col2, col3, col4 = st.columns(4)

    try:
        # Récupérer le dernier snapshot via l'API
        latest = get_market_snapshot()

        with col1:
            confidence = latest.get('signal_confidence_score', 0)
            st.metric(
                label="Signal Confidence",
                value=f"{confidence:.2f}",
                delta=None
            )

        with col2:
            regime = latest.get('regime_composite', 'neutral')
            regime_emoji = {
                'risk_on': '🟢',
                'risk_off': '🔴',
                'neutral': '⚪',
                'volatile': '🟠'
            }
            st.metric(
                label="Régime de marché",
                value=f"{regime_emoji.get(regime, '⚪')} {regime.upper()}"
            )

        with col3:
            vol_regime = latest.get('volatility_regime', 'normal')
            st.metric(
                label="Volatilité",
                value=vol_regime.upper()
            )

        with col4:
            event_active = latest.get('event_window_active', False)
            st.metric(
                label="Event Window",
                value="🔴 ACTIF" if event_active else "🟢 INACTIF"
            )

    except Exception as e:
        st.error(f"Erreur lors de la récupération des données: {e}")
