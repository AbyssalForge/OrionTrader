"""
Tab Prix & Signaux - Graphiques de prix et signaux
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from utils.database import get_db_connection


def render_prices_tab():
    st.subheader("EUR/USD M15 - Prix et signaux")

    try:
        conn = get_db_connection()
        df = pd.read_sql("""
            SELECT m.time, m.open, m.high, m.low, m.close, m.volatility_1h,
                   s.signal_confidence_score, s.regime_composite
            FROM mt5_eurusd_m15 m
            JOIN market_snapshot_m15 s ON m.time = s.mt5_time
            ORDER BY m.time DESC
            LIMIT 100
        """, conn)
        conn.close()

        df = df.sort_values('time')

        if len(df) == 0:
            st.warning("Aucune donnée disponible.")
            return

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
            xaxis_title="Date",
            height=500,
            xaxis_rangeslider_visible=False
        )
        st.plotly_chart(fig, use_container_width=True)

        fig2 = px.line(
            df, x='time', y='signal_confidence_score',
            title='Score de confiance du signal',
            labels={'signal_confidence_score': 'Confiance', 'time': 'Date'}
        )
        fig2.add_hline(y=0.7, line_dash="dash", line_color="green")
        fig2.add_hline(y=0.3, line_dash="dash", line_color="red")
        st.plotly_chart(fig2, use_container_width=True)

    except Exception as e:
        st.error(f"Erreur lors du chargement des données : {e}")
