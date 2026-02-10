"""
Page Analytics - Analyse approfondie des données
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys

sys.path.insert(0, '/opt/airflow')

from utils.database import get_db_session

st.set_page_config(
    page_title="Analytics - OrionTrader",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Analytics - Analyse Approfondie")


with st.sidebar:
    st.subheader("Filtres")

    period_days = st.slider("Période (jours)", 1, 30, 7)

    regime_filter = st.multiselect(
        "Régimes de marché",
        ["risk_on", "risk_off", "neutral", "volatile"],
        default=["risk_on", "risk_off", "neutral", "volatile"]
    )

    vol_filter = st.multiselect(
        "Régimes de volatilité",
        ["low", "normal", "high"],
        default=["low", "normal", "high"]
    )


st.subheader("📈 Évolution des métriques")

try:
    session = get_db_session()
    from models import MarketSnapshotM15

    end_time = datetime.now()
    start_time = end_time - timedelta(days=period_days)

    query = session.query(
        MarketSnapshotM15.time,
        MarketSnapshotM15.signal_confidence_score,
        MarketSnapshotM15.signal_divergence_count,
        MarketSnapshotM15.trend_strength_composite,
        MarketSnapshotM15.regime_composite,
        MarketSnapshotM15.volatility_regime
    ).filter(
        MarketSnapshotM15.time >= start_time,
        MarketSnapshotM15.regime_composite.in_(regime_filter),
        MarketSnapshotM15.volatility_regime.in_(vol_filter)
    ).order_by(MarketSnapshotM15.time.asc())

    df = pd.read_sql(query.statement, session.bind)

    if len(df) > 0:
        fig1 = px.line(
            df,
            x='time',
            y='signal_confidence_score',
            title='Signal Confidence Score (évolution)',
            labels={'signal_confidence_score': 'Confidence', 'time': 'Temps'}
        )
        fig1.add_hline(y=0.7, line_dash="dash", line_color="green")
        fig1.add_hline(y=0.3, line_dash="dash", line_color="red")
        st.plotly_chart(fig1, use_container_width=True)

        col1, col2 = st.columns(2)

        with col1:
            fig2 = px.line(
                df,
                x='time',
                y='trend_strength_composite',
                title='Trend Strength Composite',
                labels={'trend_strength_composite': 'Trend Strength', 'time': 'Temps'}
            )
            fig2.add_hline(y=0, line_dash="dash", line_color="gray")
            st.plotly_chart(fig2, use_container_width=True)

        with col2:
            fig3 = px.bar(
                df,
                x='time',
                y='signal_divergence_count',
                title='Signal Divergence Count',
                labels={'signal_divergence_count': 'Divergences', 'time': 'Temps'}
            )
            st.plotly_chart(fig3, use_container_width=True)

    else:
        st.warning("Aucune donnée pour les filtres sélectionnés")

    session.close()

except Exception as e:
    st.error(f"Erreur: {e}")


st.divider()
st.subheader("🔗 Analyse de Corrélation")

try:
    session = get_db_session()
    from models import MarketSnapshotM15, MT5EURUSDM15, YahooFinanceDaily

    query = session.query(
        MarketSnapshotM15.signal_confidence_score,
        MarketSnapshotM15.trend_strength_composite,
        MarketSnapshotM15.signal_divergence_count,
        MT5EURUSDM15.volatility_1h,
        MT5EURUSDM15.volatility_4h,
        YahooFinanceDaily.vix_close,
        YahooFinanceDaily.dxy_close
    ).join(
        MT5EURUSDM15,
        MarketSnapshotM15.mt5_time == MT5EURUSDM15.time
    ).join(
        YahooFinanceDaily,
        MarketSnapshotM15.yahoo_time == YahooFinanceDaily.time
    ).filter(
        MarketSnapshotM15.time >= start_time
    ).limit(1000)

    df_corr = pd.read_sql(query.statement, session.bind)

    if len(df_corr) > 5:
        corr_matrix = df_corr.corr()

        fig = px.imshow(
            corr_matrix,
            text_auto='.2f',
            aspect='auto',
            color_continuous_scale='RdBu_r',
            title='Matrice de Corrélation',
            labels=dict(color="Corrélation")
        )

        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 🔝 Corrélations les plus fortes")

        corr_pairs = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                corr_pairs.append({
                    'Variable 1': corr_matrix.columns[i],
                    'Variable 2': corr_matrix.columns[j],
                    'Corrélation': corr_matrix.iloc[i, j]
                })

        df_pairs = pd.DataFrame(corr_pairs)
        df_pairs = df_pairs.sort_values('Corrélation', key=abs, ascending=False)

        st.dataframe(
            df_pairs.head(10),
            use_container_width=True,
            hide_index=True
        )

    session.close()

except Exception as e:
    st.error(f"Erreur lors de l'analyse de corrélation: {e}")


st.divider()
st.subheader("📊 Statistiques Descriptives")

try:
    session = get_db_session()
    from models import MarketSnapshotM15

    query = session.query(
        MarketSnapshotM15.signal_confidence_score,
        MarketSnapshotM15.signal_divergence_count,
        MarketSnapshotM15.trend_strength_composite
    ).filter(
        MarketSnapshotM15.time >= start_time,
        MarketSnapshotM15.regime_composite.in_(regime_filter),
        MarketSnapshotM15.volatility_regime.in_(vol_filter)
    )

    df_stats = pd.read_sql(query.statement, session.bind)

    if len(df_stats) > 0:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Moyenne Confidence",
                f"{df_stats['signal_confidence_score'].mean():.3f}",
                f"σ = {df_stats['signal_confidence_score'].std():.3f}"
            )

        with col2:
            st.metric(
                "Moyenne Divergences",
                f"{df_stats['signal_divergence_count'].mean():.2f}",
                f"Max = {df_stats['signal_divergence_count'].max():.0f}"
            )

        with col3:
            st.metric(
                "Moyenne Trend Strength",
                f"{df_stats['trend_strength_composite'].mean():.4f}",
                f"σ = {df_stats['trend_strength_composite'].std():.4f}"
            )

        st.markdown("### 📊 Distributions")

        col1, col2 = st.columns(2)

        with col1:
            fig = px.histogram(
                df_stats,
                x='signal_confidence_score',
                nbins=30,
                title='Distribution Signal Confidence',
                labels={'signal_confidence_score': 'Confidence Score'}
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.histogram(
                df_stats,
                x='trend_strength_composite',
                nbins=30,
                title='Distribution Trend Strength',
                labels={'trend_strength_composite': 'Trend Strength'}
            )
            st.plotly_chart(fig, use_container_width=True)

    session.close()

except Exception as e:
    st.error(f"Erreur: {e}")
