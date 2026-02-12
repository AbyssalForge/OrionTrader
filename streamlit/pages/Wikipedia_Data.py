"""
OrionTrader - Page Wikipedia Data
Visualisation des données d'indices boursiers scrapées depuis Wikipedia
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from utils.database import get_db_connection
except ImportError:
    def get_db_connection():
        return None

st.set_page_config(
    page_title="Wikipedia Data - OrionTrader",
    page_icon="🏦",
    layout="wide"
)


def load_wikipedia_data():
    """Charger les données Wikipedia depuis PostgreSQL"""
    conn = get_db_connection()
    if conn is None:
        return None, "Impossible de se connecter à la base de données"

    try:
        query = """
        SELECT
            ticker,
            company_name,
            sector,
            country,
            region,
            index_name,
            index_key,
            num_indices,
            is_multi_index,
            scraped_at
        FROM wikipedia_indices
        ORDER BY ticker
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df, None

    except Exception as e:
        conn.close()
        return None, str(e)

def create_sample_data():
    """Créer des données d'exemple si la DB n'est pas disponible"""
    return pd.DataFrame({
        'ticker': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'MC.PA', 'OR.PA', 'SAN.PA'],
        'company_name': ['Apple Inc.', 'Microsoft Corp.', 'Alphabet Inc.', 'Amazon.com Inc.',
                        'Tesla Inc.', 'LVMH', 'L\'Oréal', 'Sanofi'],
        'sector': ['Technology', 'Technology', 'Technology', 'Consumer Cyclical',
                  'Consumer Cyclical', 'Consumer Cyclical', 'Healthcare', 'Healthcare'],
        'country': ['USA', 'USA', 'USA', 'USA', 'USA', 'France', 'France', 'France'],
        'region': ['North America', 'North America', 'North America', 'North America',
                  'North America', 'Europe', 'Europe', 'Europe'],
        'index_name': ['S&P 500', 'S&P 500', 'NASDAQ 100', 'S&P 500',
                      'NASDAQ 100', 'CAC 40', 'CAC 40', 'CAC 40'],
        'index_key': ['SP500', 'SP500', 'NASDAQ100', 'SP500', 'NASDAQ100', 'CAC40', 'CAC40', 'CAC40'],
        'num_indices': [2, 2, 1, 2, 1, 1, 1, 1],
        'is_multi_index': [True, True, False, True, False, False, False, False],
        'scraped_at': [datetime.now()] * 8
    })


st.title("🏦 Données Wikipedia - Indices Boursiers")
st.markdown("Exploration des données d'indices boursiers scrapées depuis Wikipedia")

st.divider()


with st.spinner("📥 Chargement des données..."):
    df, error = load_wikipedia_data()

    if error:
        st.error(f"❌ Erreur DB : {error}")
        st.warning("Affichage de données d'exemple.")
        df = create_sample_data()
    elif df is None or df.empty:
        st.warning("⚠️ Table wikipedia_indices vide ou introuvable. Affichage de données d'exemple.")
        df = create_sample_data()

st.success(f"✅ **{len(df)}** entreprises chargées")


with st.sidebar:
    st.header("🔍 Filtres")

    indices = ['Tous'] + sorted(df['index_name'].unique().tolist())
    selected_index = st.selectbox("📈 Indice boursier", indices)

    sectors = ['Tous'] + sorted(df['sector'].dropna().unique().tolist())
    selected_sector = st.selectbox("🏢 Secteur", sectors)

    countries = ['Tous'] + sorted(df['country'].dropna().unique().tolist())
    selected_country = st.selectbox("🌍 Pays", countries)

    show_multi_index = st.checkbox("Afficher uniquement les multi-indices", False)

    st.divider()

    st.subheader("🔎 Recherche")
    search_term = st.text_input("Ticker ou Entreprise", "").upper()

filtered_df = df.copy()

if selected_index != 'Tous':
    filtered_df = filtered_df[filtered_df['index_name'] == selected_index]

if selected_sector != 'Tous':
    filtered_df = filtered_df[filtered_df['sector'] == selected_sector]

if selected_country != 'Tous':
    filtered_df = filtered_df[filtered_df['country'] == selected_country]

if show_multi_index:
    filtered_df = filtered_df[filtered_df['is_multi_index'] == True]

if search_term:
    filtered_df = filtered_df[
        filtered_df['ticker'].str.contains(search_term, na=False) |
        filtered_df['company_name'].str.contains(search_term, case=False, na=False)
    ]

st.info(f"📊 **{len(filtered_df)}** entreprises après filtrage")


st.header("📊 Statistiques")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "📈 Indices",
        len(filtered_df['index_name'].unique()),
        help="Nombre d'indices uniques"
    )

with col2:
    st.metric(
        "🏢 Secteurs",
        len(filtered_df['sector'].dropna().unique()),
        help="Nombre de secteurs uniques"
    )

with col3:
    st.metric(
        "🌍 Pays",
        len(filtered_df['country'].dropna().unique()),
        help="Nombre de pays uniques"
    )

with col4:
    multi_index_pct = (filtered_df['is_multi_index'].sum() / len(filtered_df) * 100) if len(filtered_df) > 0 else 0
    st.metric(
        "🔗 Multi-indices",
        f"{multi_index_pct:.1f}%",
        help="% d'entreprises présentes dans plusieurs indices"
    )

st.divider()


st.header("📊 Visualisations")

tab1, tab2, tab3 = st.tabs(["📈 Par Indice", "🏢 Par Secteur", "🌍 Par Pays"])

with tab1:
    if not filtered_df.empty:
        index_counts = filtered_df['index_name'].value_counts()

        fig_index = px.bar(
            x=index_counts.values,
            y=index_counts.index,
            orientation='h',
            title="Nombre d'entreprises par indice",
            labels={'x': 'Nombre d\'entreprises', 'y': 'Indice'},
            color=index_counts.values,
            color_continuous_scale='Blues'
        )
        fig_index.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_index, use_container_width=True)
    else:
        st.info("Aucune donnée à afficher")

with tab2:
    if not filtered_df.empty and 'sector' in filtered_df.columns:
        sector_counts = filtered_df['sector'].dropna().value_counts()

        fig_sector = px.pie(
            values=sector_counts.values,
            names=sector_counts.index,
            title="Répartition par secteur",
            hole=0.4
        )
        fig_sector.update_layout(height=500)
        st.plotly_chart(fig_sector, use_container_width=True)
    else:
        st.info("Aucune donnée de secteur disponible")

with tab3:
    if not filtered_df.empty and 'country' in filtered_df.columns:
        country_counts = filtered_df['country'].dropna().value_counts()

        fig_country = px.bar(
            x=country_counts.index,
            y=country_counts.values,
            title="Nombre d'entreprises par pays",
            labels={'x': 'Pays', 'y': 'Nombre d\'entreprises'},
            color=country_counts.values,
            color_continuous_scale='Greens'
        )
        fig_country.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig_country, use_container_width=True)
    else:
        st.info("Aucune donnée de pays disponible")

st.divider()


st.header("📋 Données détaillées")

display_columns = [
    'ticker',
    'company_name',
    'sector',
    'country',
    'index_name',
    'num_indices',
    'is_multi_index'
]

available_columns = [col for col in display_columns if col in filtered_df.columns]

if not filtered_df.empty:
    column_config = {
        "ticker": st.column_config.TextColumn("Ticker", width="small"),
        "company_name": st.column_config.TextColumn("Entreprise", width="large"),
        "sector": st.column_config.TextColumn("Secteur", width="medium"),
        "country": st.column_config.TextColumn("Pays", width="small"),
        "index_name": st.column_config.TextColumn("Indice", width="medium"),
        "num_indices": st.column_config.NumberColumn("Nb Indices", width="small"),
        "is_multi_index": st.column_config.CheckboxColumn("Multi-indice", width="small")
    }

    st.dataframe(
        filtered_df[available_columns],
        use_container_width=True,
        hide_index=True,
        column_config=column_config,
        height=400
    )

    csv = filtered_df[available_columns].to_csv(index=False).encode('utf-8')

    st.download_button(
        label="📥 Télécharger en CSV",
        data=csv,
        file_name=f"wikipedia_indices_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True
    )
else:
    st.warning("Aucune donnée ne correspond aux filtres sélectionnés")


st.divider()

st.header("🏆 Top Entreprises")

col1, col2 = st.columns(2)

with col1:
    st.subheader("🔗 Entreprises multi-indices")
    multi_index_companies = filtered_df[filtered_df['is_multi_index'] == True].sort_values(
        'num_indices', ascending=False
    ).head(10)

    if not multi_index_companies.empty:
        for _, row in multi_index_companies.iterrows():
            st.markdown(f"**{row['ticker']}** - {row['company_name']}")
            st.caption(f"Présent dans {row['num_indices']} indices | {row['sector']} | {row['country']}")
    else:
        st.info("Aucune entreprise multi-indices dans les données filtrées")

with col2:
    st.subheader("🏢 Secteurs principaux")
    if not filtered_df.empty and 'sector' in filtered_df.columns:
        sector_stats = filtered_df.groupby('sector').agg({
            'ticker': 'count',
            'is_multi_index': 'sum'
        }).sort_values('ticker', ascending=False).head(5)

        for sector, row in sector_stats.iterrows():
            st.markdown(f"**{sector}**")
            st.caption(f"{row['ticker']} entreprises | {int(row['is_multi_index'])} multi-indices")
    else:
        st.info("Aucune donnée de secteur disponible")


st.divider()

st.caption(f"""
📅 Dernière mise à jour: {df['scraped_at'].max().strftime('%Y-%m-%d %H:%M:%S') if 'scraped_at' in df.columns and not df.empty else 'N/A'}

ℹ️ **Source**: Données scrapées depuis Wikipedia (CAC 40, S&P 500, NASDAQ 100, Dow Jones)
""")
