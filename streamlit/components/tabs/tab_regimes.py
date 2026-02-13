"""
Tab Régimes - Distribution des régimes de marché
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from utils.database import get_db_connection


def render_regimes_tab():
    st.subheader("Régimes de marché")

    try:
        conn = get_db_connection()
        df_regimes = pd.read_sql("""
            SELECT regime_composite, volatility_regime
            FROM market_snapshot_m15
            ORDER BY time DESC
            LIMIT 1000
        """, conn)
        conn.close()

        if len(df_regimes) == 0:
            st.warning("Aucune donnée disponible.")
            return

        col1, col2 = st.columns(2)

        with col1:
            regime_counts = df_regimes['regime_composite'].value_counts()
            fig = px.pie(
                values=regime_counts.values,
                names=regime_counts.index,
                title='Régime de marché (1000 dernières bougies)',
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
                title='Volatilité (1000 dernières bougies)',
                color_discrete_map={
                    'low': '#00CC96',
                    'normal': '#636EFA',
                    'high': '#EF553B'
                }
            )
            st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Erreur : {e}")
