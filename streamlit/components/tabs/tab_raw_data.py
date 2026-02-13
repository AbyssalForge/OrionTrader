"""
Tab Données brutes - Export et consultation des données de marché
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from utils.database import get_db_connection


def render_raw_data_tab():
    st.subheader("Données brutes - Market Snapshot")

    try:
        conn = get_db_connection()

        limit = st.selectbox("Nombre de lignes", [100, 500, 1000, 5000], index=0)

        df_raw = pd.read_sql(f"""
            SELECT *
            FROM market_snapshot_m15
            ORDER BY time DESC
            LIMIT {limit}
        """, conn)
        conn.close()

        if len(df_raw) == 0:
            st.warning("Aucune donnée disponible.")
            return

        st.dataframe(df_raw, use_container_width=True, hide_index=True)

        st.divider()

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Lignes", f"{len(df_raw):,}")

        with col2:
            avg_confidence = df_raw['signal_confidence_score'].mean()
            st.metric("Confiance moyenne", f"{avg_confidence:.3f}")

        with col3:
            regime_mode = df_raw['regime_composite'].mode()[0]
            st.metric("Régime dominant", regime_mode.upper())

        with col4:
            high_confidence_pct = (
                (df_raw['signal_confidence_score'] > 0.7).sum() / len(df_raw) * 100
            )
            st.metric("Signaux > 0.7", f"{high_confidence_pct:.1f}%")

        st.divider()

        csv = df_raw.to_csv(index=False)
        st.download_button(
            label="Télécharger CSV",
            data=csv,
            file_name=f"market_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )

    except Exception as e:
        st.error(f"Erreur : {e}")
