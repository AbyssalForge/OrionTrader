"""
Tab Régimes - Distribution des régimes de marché
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import sys

sys.path.insert(0, '/opt/airflow')

from utils.database import get_db_session
from models import MarketSnapshotM15


def render_regimes_tab():
    """Affiche l'onglet Régimes"""
    st.subheader("Distribution des Régimes de Marché")

    try:
        session = get_db_session()

        query = session.query(
            MarketSnapshotM15.regime_composite,
            MarketSnapshotM15.volatility_regime
        ).order_by(
            MarketSnapshotM15.time.desc()
        ).limit(1000)

        df_regimes = pd.read_sql(query.statement, session.bind)

        if len(df_regimes) == 0:
            st.warning("Aucune donnée disponible")
            session.close()
            return

        col1, col2 = st.columns(2)

        with col1:
            regime_counts = df_regimes['regime_composite'].value_counts()
            fig = px.pie(
                values=regime_counts.values,
                names=regime_counts.index,
                title='Régime de Marché (1000 dernières bougies)',
                color_discrete_map={
                    'risk_on': '#00CC96',
                    'risk_off': '#EF553B',
                    'neutral': '#636EFA',
                    'volatile': '#FFA15A'
                }
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            vol_counts = df_regimes['volatility_regime'].value_counts()
            fig = px.pie(
                values=vol_counts.values,
                names=vol_counts.index,
                title='Régime de Volatilité (1000 dernières bougies)',
                color_discrete_map={
                    'low': '#00CC96',
                    'normal': '#636EFA',
                    'high': '#EF553B'
                }
            )
            st.plotly_chart(fig, use_container_width=True)

        session.close()

    except Exception as e:
        st.error(f"Erreur: {e}")
