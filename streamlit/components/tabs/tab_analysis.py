"""
Tab Analyse - Opportunités et alertes de marché
"""

import streamlit as st
import pandas as pd
from utils.database import get_db_connection


def render_analysis_tab():
    st.subheader("Analyse du marché")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Opportunités détectées")

        try:
            conn = get_db_connection()
            df_opps = pd.read_sql("""
                SELECT time, signal_confidence_score, regime_composite, volatility_regime
                FROM market_snapshot_m15
                WHERE signal_confidence_score > 0.6
                  AND event_window_active = false
                ORDER BY signal_confidence_score DESC
                LIMIT 10
            """, conn)
            conn.close()

            if len(df_opps) > 0:
                df_opps.columns = ['Temps', 'Confiance', 'Régime', 'Volatilité']
                st.dataframe(df_opps, use_container_width=True, hide_index=True)
            else:
                st.info("Aucune opportunité détectée actuellement.")

        except Exception as e:
            st.error(f"Erreur : {e}")

    with col2:
        st.markdown("### Alertes de divergence")

        try:
            conn = get_db_connection()
            df_alerts = pd.read_sql("""
                SELECT time, signal_divergence_count, regime_composite
                FROM market_snapshot_m15
                WHERE signal_divergence_count > 1
                ORDER BY time DESC
                LIMIT 10
            """, conn)
            conn.close()

            if len(df_alerts) > 0:
                df_alerts.columns = ['Temps', 'Divergences', 'Régime']
                st.dataframe(df_alerts, use_container_width=True, hide_index=True)
            else:
                st.success("Aucune divergence détectée.")

        except Exception as e:
            st.error(f"Erreur : {e}")
