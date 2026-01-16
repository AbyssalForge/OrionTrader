"""
Tab Analyse - Opportunités et alertes
"""

import streamlit as st
import pandas as pd
import sys

# Ajouter le path des models Airflow
sys.path.insert(0, '/opt/airflow')

from utils.database import get_db_session
from models import MarketSnapshotM15


def render_analysis_tab():
    """Affiche l'onglet Analyse"""
    st.subheader("Analyse Détaillée")

    col1, col2 = st.columns(2)

    # ====================================================================
    # OPPORTUNITÉS ACTUELLES
    # ====================================================================
    with col1:
        st.markdown("### 🎯 Opportunités Actuelles")

        try:
            session = get_db_session()

            # Requête pour les meilleurs signaux
            query = session.query(MarketSnapshotM15).filter(
                MarketSnapshotM15.signal_confidence_score > 0.6,
                MarketSnapshotM15.event_window_active == False
            ).order_by(
                MarketSnapshotM15.signal_confidence_score.desc()
            ).limit(10)

            df_opps = pd.read_sql(query.statement, session.bind)

            if len(df_opps) > 0:
                # Sélectionner uniquement les colonnes pertinentes
                df_display = df_opps[[
                    'time',
                    'signal_confidence_score',
                    'regime_composite',
                    'volatility_regime'
                ]].copy()

                # Renommer pour affichage
                df_display.columns = [
                    'Temps',
                    'Confidence',
                    'Régime',
                    'Volatilité'
                ]

                st.dataframe(
                    df_display,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Aucune opportunité détectée actuellement")

            session.close()

        except Exception as e:
            st.error(f"Erreur: {e}")

    # ====================================================================
    # ALERTES DE DIVERGENCE
    # ====================================================================
    with col2:
        st.markdown("### ⚠️ Alertes")

        try:
            session = get_db_session()

            # Requête pour les divergences
            query = session.query(MarketSnapshotM15).filter(
                MarketSnapshotM15.signal_divergence_count > 1
            ).order_by(
                MarketSnapshotM15.time.desc()
            ).limit(10)

            df_alerts = pd.read_sql(query.statement, session.bind)

            if len(df_alerts) > 0:
                # Sélectionner uniquement les colonnes pertinentes
                df_display = df_alerts[[
                    'time',
                    'signal_divergence_count',
                    'regime_composite'
                ]].copy()

                # Renommer pour affichage
                df_display.columns = [
                    'Temps',
                    'Divergences',
                    'Régime'
                ]

                st.dataframe(
                    df_display,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.success("Aucune divergence détectée")

            session.close()

        except Exception as e:
            st.error(f"Erreur: {e}")
