"""
Tab Données Brutes - Export et consultation des données
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys

sys.path.insert(0, '/opt/airflow')

from utils.database import get_db_session
from models import MarketSnapshotM15


def render_raw_data_tab():
    """Affiche l'onglet Données Brutes"""
    st.subheader("Données Brutes - Market Snapshot")

    try:
        session = get_db_session()

        col1, col2 = st.columns([3, 1])

        with col2:
            limit = st.selectbox(
                "Nombre de lignes",
                [100, 500, 1000, 5000],
                index=0
            )

        query = session.query(MarketSnapshotM15).order_by(
            MarketSnapshotM15.time.desc()
        ).limit(limit)

        df_raw = pd.read_sql(query.statement, session.bind)

        if len(df_raw) == 0:
            st.warning("Aucune donnée disponible")
            session.close()
            return

        st.dataframe(df_raw, use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("### 📊 Statistiques")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Total lignes",
                f"{len(df_raw):,}"
            )

        with col2:
            avg_confidence = df_raw['signal_confidence_score'].mean()
            st.metric(
                "Confidence moyenne",
                f"{avg_confidence:.3f}"
            )

        with col3:
            regime_mode = df_raw['regime_composite'].mode()[0]
            st.metric(
                "Régime dominant",
                regime_mode.upper()
            )

        with col4:
            high_confidence_pct = (
                (df_raw['signal_confidence_score'] > 0.7).sum() / len(df_raw) * 100
            )
            st.metric(
                "Signaux > 0.7",
                f"{high_confidence_pct:.1f}%"
            )

        st.divider()

        csv = df_raw.to_csv(index=False)
        st.download_button(
            label="📥 Télécharger CSV",
            data=csv,
            file_name=f"market_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

        session.close()

    except Exception as e:
        st.error(f"Erreur: {e}")
