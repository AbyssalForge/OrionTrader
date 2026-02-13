"""
OrionTrader - Analyse des marchés
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

from utils.database import get_db_connection

st.set_page_config(
    page_title="Analyse des marchés - OrionTrader",
    layout="wide"
)

st.title("Analyse des marchés EUR/USD")

with st.sidebar:
    st.subheader("Filtres")

    period_days = st.slider("Période (jours)", 1, 30, 7)

    regime_filter = st.multiselect(
        "Régime de marché",
        ["risk_on", "risk_off", "neutral", "volatile"],
        default=["risk_on", "risk_off", "neutral", "volatile"]
    )

    vol_filter = st.multiselect(
        "Volatilité",
        ["low", "normal", "high"],
        default=["low", "normal", "high"]
    )

end_time = datetime.now()
start_time = end_time - timedelta(days=period_days)

regime_list = ", ".join(f"'{r}'" for r in regime_filter) if regime_filter else "''"
vol_list = ", ".join(f"'{v}'" for v in vol_filter) if vol_filter else "''"


# ─── Section 1 : Signaux ───────────────────────────────────────────────────
st.subheader("Évolution des signaux")

try:
    conn = get_db_connection()
    df = pd.read_sql(f"""
        SELECT time, signal_confidence_score, signal_divergence_count,
               trend_strength_composite, regime_composite, volatility_regime
        FROM market_snapshot_m15
        WHERE time >= '{start_time}'
          AND regime_composite IN ({regime_list})
          AND volatility_regime IN ({vol_list})
        ORDER BY time ASC
    """, conn)
    conn.close()

    if len(df) > 0:
        fig1 = px.line(
            df, x='time', y='signal_confidence_score',
            title='Score de confiance du signal',
            labels={'signal_confidence_score': 'Confiance', 'time': 'Date'}
        )
        fig1.add_hline(y=0.7, line_dash="dash", line_color="green")
        fig1.add_hline(y=0.3, line_dash="dash", line_color="red")
        st.plotly_chart(fig1, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            fig2 = px.line(
                df, x='time', y='trend_strength_composite',
                title='Force de tendance',
                labels={'trend_strength_composite': 'Tendance', 'time': 'Date'}
            )
            fig2.add_hline(y=0, line_dash="dash", line_color="gray")
            st.plotly_chart(fig2, use_container_width=True)

        with col2:
            fig3 = px.bar(
                df, x='time', y='signal_divergence_count',
                title='Divergences de signal',
                labels={'signal_divergence_count': 'Divergences', 'time': 'Date'}
            )
            st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("Aucune donnée pour les filtres sélectionnés.")

except Exception as e:
    st.error(f"Erreur : {e}")


# ─── Section 2 : Corrélations ─────────────────────────────────────────────
st.divider()
st.subheader("Corrélations entre indicateurs")

try:
    conn = get_db_connection()
    df_corr = pd.read_sql(f"""
        SELECT
            s.signal_confidence_score,
            s.trend_strength_composite,
            s.signal_divergence_count,
            m.volatility_1h,
            m.volatility_4h,
            y.vix_close,
            y.dxy_close
        FROM market_snapshot_m15 s
        JOIN mt5_eurusd_m15 m ON s.mt5_time = m.time
        JOIN yahoo_finance_daily y ON s.yahoo_time = y.time
        WHERE s.time >= '{start_time}'
        LIMIT 1000
    """, conn)
    conn.close()

    if len(df_corr) > 5:
        corr_matrix = df_corr.corr()
        fig = px.imshow(
            corr_matrix,
            text_auto='.2f',
            aspect='auto',
            color_continuous_scale='RdBu_r',
            title='Matrice de corrélation',
            labels=dict(color="Corrélation")
        )
        st.plotly_chart(fig, use_container_width=True)

        corr_pairs = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                corr_pairs.append({
                    'Variable 1': corr_matrix.columns[i],
                    'Variable 2': corr_matrix.columns[j],
                    'Corrélation': corr_matrix.iloc[i, j]
                })

        df_pairs = pd.DataFrame(corr_pairs).sort_values('Corrélation', key=abs, ascending=False)
        st.subheader("Corrélations les plus fortes")
        st.dataframe(df_pairs.head(10), use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Erreur lors de l'analyse de corrélation : {e}")


# ─── Section 3 : Statistiques ─────────────────────────────────────────────
st.divider()
st.subheader("Statistiques descriptives")

try:
    conn = get_db_connection()
    df_stats = pd.read_sql(f"""
        SELECT signal_confidence_score, signal_divergence_count, trend_strength_composite
        FROM market_snapshot_m15
        WHERE time >= '{start_time}'
          AND regime_composite IN ({regime_list})
          AND volatility_regime IN ({vol_list})
    """, conn)
    conn.close()

    if len(df_stats) > 0:
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Confiance moyenne",
                f"{df_stats['signal_confidence_score'].mean():.3f}",
                f"σ = {df_stats['signal_confidence_score'].std():.3f}"
            )
        with col2:
            st.metric(
                "Divergences moyennes",
                f"{df_stats['signal_divergence_count'].mean():.2f}",
                f"Max = {df_stats['signal_divergence_count'].max():.0f}"
            )
        with col3:
            st.metric(
                "Force de tendance moyenne",
                f"{df_stats['trend_strength_composite'].mean():.4f}",
                f"σ = {df_stats['trend_strength_composite'].std():.4f}"
            )

        col1, col2 = st.columns(2)
        with col1:
            fig = px.histogram(
                df_stats, x='signal_confidence_score', nbins=30,
                title='Distribution de la confiance',
                labels={'signal_confidence_score': 'Score de confiance'}
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.histogram(
                df_stats, x='trend_strength_composite', nbins=30,
                title='Distribution de la force de tendance',
                labels={'trend_strength_composite': 'Force de tendance'}
            )
            st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Erreur : {e}")
