"""
Tab Prix & Signaux - Graphiques de prix et signaux
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sys

# Ajouter le path des models Airflow
sys.path.insert(0, '/opt/airflow')

from utils.database import get_db_session
from models import MT5EURUSDM15, MarketSnapshotM15


def render_prices_tab():
    """Affiche l'onglet Prix & Signaux"""
    st.subheader("EUR/USD M15 - Prix et Signaux")

    try:
        session = get_db_session()

        # Requête pour les dernières 100 bougies
        query = session.query(
            MT5EURUSDM15.time,
            MT5EURUSDM15.open,
            MT5EURUSDM15.high,
            MT5EURUSDM15.low,
            MT5EURUSDM15.close,
            MT5EURUSDM15.volatility_1h,
            MarketSnapshotM15.signal_confidence_score,
            MarketSnapshotM15.regime_composite
        ).join(
            MarketSnapshotM15,
            MT5EURUSDM15.time == MarketSnapshotM15.mt5_time
        ).order_by(
            MT5EURUSDM15.time.desc()
        ).limit(100)

        df = pd.read_sql(query.statement, session.bind)
        df = df.sort_values('time')

        if len(df) == 0:
            st.warning("Aucune donnée disponible")
            session.close()
            return

        # ====================================================================
        # GRAPHIQUE CHANDELIER
        # ====================================================================
        fig = go.Figure(data=[go.Candlestick(
            x=df['time'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='EUR/USD'
        )])

        fig.update_layout(
            title="EUR/USD M15",
            yaxis_title="Prix",
            xaxis_title="Temps",
            height=500,
            xaxis_rangeslider_visible=False
        )

        st.plotly_chart(fig, use_container_width=True)

        # ====================================================================
        # GRAPHIQUE SIGNAL CONFIDENCE
        # ====================================================================
        fig2 = px.line(
            df,
            x='time',
            y='signal_confidence_score',
            title='Signal Confidence Score',
            labels={'signal_confidence_score': 'Confidence', 'time': 'Temps'}
        )
        fig2.add_hline(
            y=0.7,
            line_dash="dash",
            line_color="green",
            annotation_text="Seuil élevé"
        )
        fig2.add_hline(
            y=0.3,
            line_dash="dash",
            line_color="red",
            annotation_text="Seuil bas"
        )

        st.plotly_chart(fig2, use_container_width=True)

        session.close()

    except Exception as e:
        st.error(f"Erreur lors du chargement des données: {e}")
