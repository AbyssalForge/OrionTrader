"""
OrionTrader - Analyse des marchés
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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


# ─── Section 1 : Synthèse du marché ────────────────────────────────────────
st.subheader("Synthèse du marché")

try:
    conn = get_db_connection()
    df_latest = pd.read_sql("""
        SELECT regime_composite, volatility_regime, signal_confidence_score
        FROM market_snapshot_m15
        ORDER BY time DESC
        LIMIT 1
    """, conn)
    conn.close()

    if len(df_latest) > 0:
        row = df_latest.iloc[0]

        col1, col2, col3 = st.columns(3)

        regime_labels = {
            'risk_on': 'Haussier',
            'risk_off': 'Baissier',
            'neutral': 'Neutre',
            'volatile': 'Volatile'
        }
        vol_labels = {
            'low': 'Faible',
            'normal': 'Normale',
            'high': 'Élevée'
        }

        with col1:
            regime = row['regime_composite']
            st.metric("Régime actuel", regime_labels.get(regime, regime.upper()))

        with col2:
            vol = row['volatility_regime']
            st.metric("Volatilité", vol_labels.get(vol, vol.upper()))

        with col3:
            confidence = row['signal_confidence_score']
            level = "Fort" if confidence > 0.7 else ("Modéré" if confidence > 0.4 else "Faible")
            st.metric("Signal de marché", level, f"{confidence:.0%}")

except Exception as e:
    st.error(f"Erreur : {e}")


# ─── Section 2 : Évolution EUR/USD ─────────────────────────────────────────
st.divider()
st.subheader("Évolution du cours EUR/USD")

try:
    conn = get_db_connection()
    df_price = pd.read_sql(f"""
        SELECT time, open, high, low, close
        FROM mt5_eurusd_m15
        WHERE time >= '{start_time}'
        ORDER BY time ASC
    """, conn)
    conn.close()

    if len(df_price) > 0:
        fig = go.Figure(data=[go.Candlestick(
            x=df_price['time'],
            open=df_price['open'],
            high=df_price['high'],
            low=df_price['low'],
            close=df_price['close'],
            name='EUR/USD'
        )])
        fig.update_layout(
            title=f"EUR/USD - {period_days} dernier(s) jour(s)",
            yaxis_title="Prix",
            xaxis_title="Date",
            height=450,
            xaxis_rangeslider_visible=False
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucune donnée de prix disponible.")

except Exception as e:
    st.error(f"Erreur : {e}")


# ─── Section 3 : Signaux de marché ─────────────────────────────────────────
st.divider()
st.subheader("Signaux de marché")

try:
    conn = get_db_connection()
    df_signals = pd.read_sql(f"""
        SELECT time, signal_confidence_score, regime_composite, volatility_regime
        FROM market_snapshot_m15
        WHERE time >= '{start_time}'
          AND regime_composite IN ({regime_list})
          AND volatility_regime IN ({vol_list})
        ORDER BY time ASC
    """, conn)
    conn.close()

    if len(df_signals) > 0:
        fig = px.line(
            df_signals, x='time', y='signal_confidence_score',
            title='Force du signal de marché',
            labels={'signal_confidence_score': 'Force du signal', 'time': 'Date'}
        )
        fig.add_hline(y=0.7, line_dash="dash", line_color="green",
                      annotation_text="Signal fort")
        fig.add_hline(y=0.3, line_dash="dash", line_color="red",
                      annotation_text="Signal faible")
        fig.update_yaxes(range=[0, 1], tickformat=".0%")
        st.plotly_chart(fig, use_container_width=True)

        strong = (df_signals['signal_confidence_score'] > 0.7).sum()
        total = len(df_signals)
        st.caption(f"{strong} signaux forts sur {total} observations ({strong/total:.0%}) sur la période.")
    else:
        st.info("Aucune donnée pour les filtres sélectionnés.")

except Exception as e:
    st.error(f"Erreur : {e}")


# ─── Section 4 : Indicateurs de marché ─────────────────────────────────────
st.divider()
st.subheader("Indicateurs de marché")

try:
    conn = get_db_connection()
    df_macro = pd.read_sql(f"""
        SELECT time, vix_close, dxy_close
        FROM yahoo_finance_daily
        WHERE time >= '{start_time}'
        ORDER BY time ASC
    """, conn)
    conn.close()

    if len(df_macro) > 0:
        col1, col2 = st.columns(2)

        with col1:
            fig = px.line(
                df_macro, x='time', y='vix_close',
                title='Indice de volatilité (VIX)',
                labels={'vix_close': 'VIX', 'time': 'Date'}
            )
            fig.add_hline(y=20, line_dash="dash", line_color="orange",
                          annotation_text="Seuil d'alerte")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.line(
                df_macro, x='time', y='dxy_close',
                title='Dollar Index (DXY)',
                labels={'dxy_close': 'DXY', 'time': 'Date'}
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucune donnée macro disponible pour cette période.")

except Exception as e:
    st.error(f"Erreur : {e}")


# ─── Section 5 : Répartition des régimes ───────────────────────────────────
st.divider()
st.subheader("Répartition des régimes de marché")

try:
    conn = get_db_connection()
    df_regimes = pd.read_sql(f"""
        SELECT regime_composite, volatility_regime
        FROM market_snapshot_m15
        WHERE time >= '{start_time}'
          AND regime_composite IN ({regime_list})
          AND volatility_regime IN ({vol_list})
    """, conn)
    conn.close()

    if len(df_regimes) > 0:
        col1, col2 = st.columns(2)

        with col1:
            counts = df_regimes['regime_composite'].value_counts().reset_index()
            counts.columns = ['Régime', 'Occurrences']
            counts['Régime'] = counts['Régime'].map({
                'risk_on': 'Haussier',
                'risk_off': 'Baissier',
                'neutral': 'Neutre',
                'volatile': 'Volatile'
            }).fillna(counts['Régime'])
            fig = px.pie(
                counts, values='Occurrences', names='Régime',
                title='Régime de marché',
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            counts_vol = df_regimes['volatility_regime'].value_counts().reset_index()
            counts_vol.columns = ['Volatilité', 'Occurrences']
            counts_vol['Volatilité'] = counts_vol['Volatilité'].map({
                'low': 'Faible',
                'normal': 'Normale',
                'high': 'Élevée'
            }).fillna(counts_vol['Volatilité'])
            fig = px.pie(
                counts_vol, values='Occurrences', names='Volatilité',
                title='Niveau de volatilité',
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Aucune donnée pour les filtres sélectionnés.")

except Exception as e:
    st.error(f"Erreur : {e}")
