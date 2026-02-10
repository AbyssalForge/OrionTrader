"""
OrionTrader - Page ML Model
Interface pour utiliser le modèle de prédiction ML
"""

import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import os

st.set_page_config(
    page_title="ML Model - OrionTrader",
    page_icon="🤖",
    layout="wide"
)

FASTAPI_URL = os.getenv("FASTAPI_URL", "http://fastapi:8000")

API_TOKEN = os.getenv("FASTAPI_API_TOKEN", "")


def get_headers():
    """Retourner les headers HTTP avec le token d'authentification"""
    return {
        "X-API-Key": API_TOKEN,
        "Content-Type": "application/json"
    }

def predict_single(data):
    """Faire une prédiction unique"""
    try:
        response = requests.post(
            f"{FASTAPI_URL}/model/predict",
            json=data,
            headers=get_headers(),
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Erreur lors de la prédiction: {str(e)}")
        return None

def get_model_info():
    """Récupérer les informations du modèle"""
    try:
        response = requests.get(
            f"{FASTAPI_URL}/model/info",
            headers=get_headers(),
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.warning(f"Impossible de récupérer les infos du modèle: {str(e)}")
        return None

def get_model_metrics():
    """Récupérer les métriques du modèle"""
    try:
        response = requests.get(
            f"{FASTAPI_URL}/model/metrics",
            headers=get_headers(),
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.warning(f"Impossible de récupérer les métriques: {str(e)}")
        return None

def plot_probabilities(probabilities):
    """Créer un graphique en barres des probabilités"""
    fig = go.Figure(data=[
        go.Bar(
            x=list(probabilities.keys()),
            y=list(probabilities.values()),
            text=[f"{v:.1%}" for v in probabilities.values()],
            textposition='auto',
            marker=dict(
                color=['#FF4444', '#FFA500', '#44FF44'],
                line=dict(color='white', width=2)
            )
        )
    ])

    fig.update_layout(
        title="Probabilités des classes",
        xaxis_title="Classe",
        yaxis_title="Probabilité",
        yaxis=dict(range=[0, 1], tickformat='.0%'),
        height=400,
        showlegend=False
    )

    return fig


st.title("🤖 Modèle de Prédiction ML")
st.markdown("Utilisez le modèle LightGBM pour prédire la direction du marché EUR/USD")

st.divider()


with st.sidebar:
    st.header("ℹ️ Informations du modèle")

    model_info = get_model_info()
    if model_info:
        st.metric("Nom du modèle", model_info.get("model_name", "N/A"))
        st.metric("Version", model_info.get("model_version", "N/A"))
        st.metric("Type", model_info.get("model_type", "N/A"))

        if model_info.get("loaded_at"):
            st.caption(f"Chargé le: {model_info['loaded_at'][:19]}")

    st.divider()

    st.header("📊 Métriques d'entraînement")

    metrics = get_model_metrics()
    if metrics:
        if metrics.get("balanced_accuracy"):
            st.metric("Balanced Accuracy", f"{metrics['balanced_accuracy']:.2%}")
        if metrics.get("macro_f1"):
            st.metric("Macro F1 Score", f"{metrics['macro_f1']:.2%}")
        if metrics.get("accuracy"):
            st.metric("Accuracy", f"{metrics['accuracy']:.2%}")


st.header("📈 Faire une prédiction")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 Données OHLCV (Obligatoires)")

    open_price = st.number_input(
        "Prix d'ouverture (Open)",
        min_value=0.0,
        value=1.0845,
        step=0.0001,
        format="%.4f",
        help="Prix d'ouverture de la bougie"
    )

    high_price = st.number_input(
        "Prix le plus haut (High)",
        min_value=0.0,
        value=1.0855,
        step=0.0001,
        format="%.4f",
        help="Prix le plus haut de la bougie"
    )

    low_price = st.number_input(
        "Prix le plus bas (Low)",
        min_value=0.0,
        value=1.0840,
        step=0.0001,
        format="%.4f",
        help="Prix le plus bas de la bougie"
    )

    close_price = st.number_input(
        "Prix de clôture (Close)",
        min_value=0.0,
        value=1.0850,
        step=0.0001,
        format="%.4f",
        help="Prix de clôture de la bougie"
    )

    tick_volume = st.number_input(
        "Volume (Tick Volume)",
        min_value=0,
        value=1000,
        step=100,
        help="Volume de la bougie"
    )

with col2:
    st.subheader("🌍 Indicateurs externes (Optionnels)")

    with st.expander("📈 Indices boursiers"):
        spx_close = st.number_input("S&P 500 Close", value=None, step=10.0)
        spx_trend = st.number_input("S&P 500 Trend", value=None, step=0.01)
        risk_on = st.number_input("Risk-On Score", value=None, min_value=0.0, max_value=1.0, step=0.1)

    with st.expander("🥇 Matières premières"):
        gold_close = st.number_input("Gold Close", value=None, step=10.0)
        gold_trend = st.number_input("Gold Trend", value=None, step=0.01)
        safe_haven = st.number_input("Safe Haven Score", value=None, min_value=0.0, max_value=1.0, step=0.1)

    with st.expander("💵 Dollar & Taux"):
        dxy_close = st.number_input("Dollar Index (DXY) Close", value=None, step=0.1)
        dxy_trend_1h = st.number_input("DXY Trend 1h", value=None, step=0.01)
        dxy_trend_4h = st.number_input("DXY Trend 4h", value=None, step=0.01)

        us10y_close = st.number_input("US 10Y Yield", value=None, step=0.1)
        us10y_trend = st.number_input("US 10Y Trend", value=None, step=0.01)

    with st.expander("📊 Volatilité"):
        vix_close = st.number_input("VIX Close", value=None, step=1.0)
        vix_spike = st.number_input("VIX Spike", value=None, step=0.1)

valid_input = True
if high_price < low_price:
    st.error("❌ Erreur: Le prix HIGH doit être supérieur au prix LOW")
    valid_input = False
if close_price < low_price or close_price > high_price:
    st.error("❌ Erreur: Le prix CLOSE doit être entre LOW et HIGH")
    valid_input = False
if open_price < low_price or open_price > high_price:
    st.error("❌ Erreur: Le prix OPEN doit être entre LOW et HIGH")
    valid_input = False

st.divider()

col_predict, col_clear = st.columns([1, 4])

with col_predict:
    predict_button = st.button("🎯 Prédire", type="primary", disabled=not valid_input, use_container_width=True)

with col_clear:
    if st.button("🔄 Réinitialiser"):
        st.rerun()


if predict_button and valid_input:
    prediction_data = {
        "open": open_price,
        "high": high_price,
        "low": low_price,
        "close": close_price,
        "tick_volume": tick_volume
    }

    if spx_close is not None:
        prediction_data["spx_close"] = spx_close
    if spx_trend is not None:
        prediction_data["spx_trend"] = spx_trend
    if risk_on is not None:
        prediction_data["risk_on"] = risk_on
    if gold_close is not None:
        prediction_data["gold_close"] = gold_close
    if gold_trend is not None:
        prediction_data["gold_trend"] = gold_trend
    if safe_haven is not None:
        prediction_data["safe_haven"] = safe_haven
    if dxy_close is not None:
        prediction_data["dxy_close"] = dxy_close
    if dxy_trend_1h is not None:
        prediction_data["dxy_trend_1h"] = dxy_trend_1h
    if dxy_trend_4h is not None:
        prediction_data["dxy_trend_4h"] = dxy_trend_4h
    if us10y_close is not None:
        prediction_data["us10y_close"] = us10y_close
    if us10y_trend is not None:
        prediction_data["us10y_trend"] = us10y_trend
    if vix_close is not None:
        prediction_data["vix_close"] = vix_close
    if vix_spike is not None:
        prediction_data["vix_spike"] = vix_spike

    with st.spinner("🔮 Prédiction en cours..."):
        result = predict_single(prediction_data)

    if result:
        st.success("✅ Prédiction réussie!")

        col_result1, col_result2, col_result3 = st.columns(3)

        with col_result1:
            prediction_label = result["prediction_label"]
            icon = "🔴" if prediction_label == "SHORT" else ("🟢" if prediction_label == "LONG" else "🟡")
            color = "red" if prediction_label == "SHORT" else ("green" if prediction_label == "LONG" else "orange")

            st.markdown(f"### {icon} Prédiction")
            st.markdown(f"<h1 style='color: {color};'>{prediction_label}</h1>", unsafe_allow_html=True)

        with col_result2:
            confidence = result["confidence"]
            confidence_color = "green" if confidence > 0.7 else ("orange" if confidence > 0.5 else "red")

            st.markdown("### 📊 Confiance")
            st.markdown(f"<h1 style='color: {confidence_color};'>{confidence:.1%}</h1>", unsafe_allow_html=True)

        with col_result3:
            st.markdown("### ⏱️ Timestamp")
            st.markdown(f"<h3>{result['timestamp'][:19]}</h3>", unsafe_allow_html=True)

        st.divider()

        st.plotly_chart(
            plot_probabilities(result["probabilities"]),
            use_container_width=True
        )

        st.subheader("📋 Détails des probabilités")

        prob_df = pd.DataFrame([
            {
                "Classe": "SHORT 🔴",
                "Probabilité": result["probabilities"]["SHORT"],
                "Pourcentage": f"{result['probabilities']['SHORT']:.2%}"
            },
            {
                "Classe": "NEUTRAL 🟡",
                "Probabilité": result["probabilities"]["NEUTRAL"],
                "Pourcentage": f"{result['probabilities']['NEUTRAL']:.2%}"
            },
            {
                "Classe": "LONG 🟢",
                "Probabilité": result["probabilities"]["LONG"],
                "Pourcentage": f"{result['probabilities']['LONG']:.2%}"
            }
        ])

        st.dataframe(
            prob_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Probabilité": st.column_config.ProgressColumn(
                    "Probabilité",
                    format="%.2f",
                    min_value=0,
                    max_value=1,
                )
            }
        )

        st.subheader("💡 Interprétation")

        if prediction_label == "SHORT":
            st.error("""
            **Signal de VENTE (SHORT)** 🔴

            Le modèle prédit une **baisse du prix** de l'EUR/USD.

            **Actions recommandées:**
            - Envisager une position vendeuse (SHORT)
            - Placer un stop-loss au-dessus du niveau HIGH
            - Surveiller les niveaux de support
            """)
        elif prediction_label == "LONG":
            st.success("""
            **Signal d'ACHAT (LONG)** 🟢

            Le modèle prédit une **hausse du prix** de l'EUR/USD.

            **Actions recommandées:**
            - Envisager une position acheteuse (LONG)
            - Placer un stop-loss en dessous du niveau LOW
            - Surveiller les niveaux de résistance
            """)
        else:
            st.warning("""
            **Signal NEUTRE** 🟡

            Le modèle ne détecte pas de tendance claire.

            **Actions recommandées:**
            - Attendre une confirmation supplémentaire
            - Ne pas prendre de position pour le moment
            - Surveiller l'évolution du marché
            """)

        if confidence < 0.5:
            st.warning(f"""
            ⚠️ **Attention: Confiance faible ({confidence:.1%})**

            Le modèle hésite entre plusieurs classes. Les données d'entrée sont peut-être
            hors de la distribution d'entraînement. Utilisez cette prédiction avec prudence.
            """)


st.divider()

st.caption("""
⚠️ **Disclaimer**: Ce modèle est fourni à titre informatif uniquement.
Les prédictions ne constituent pas des conseils financiers.
Le trading comporte des risques importants. Faites vos propres recherches avant de prendre toute décision d'investissement.
""")
