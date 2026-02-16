"""
OrionTrader - Prédiction EUR/USD
"""

import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import os

st.set_page_config(
    page_title="Prédiction EUR/USD - OrionTrader",
    layout="wide"
)

FASTAPI_URL = os.getenv("FASTAPI_URL", "http://fastapi:8000")
API_TOKEN = os.getenv("FASTAPI_API_TOKEN", "")


def get_headers():
    return {"X-API-Key": API_TOKEN, "Content-Type": "application/json"}


def predict_single(data):
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
        st.error(f"Erreur lors de la prédiction : {str(e)}")
        return None


def plot_probabilities(probabilities):
    fig = go.Figure(data=[
        go.Bar(
            x=list(probabilities.keys()),
            y=list(probabilities.values()),
            text=[f"{v:.1%}" for v in probabilities.values()],
            textposition='auto',
            marker=dict(
                color=['#FF4444', '#FFA500', '#44BB44'],
                line=dict(color='white', width=2)
            )
        )
    ])
    fig.update_layout(
        title="Probabilités par signal",
        xaxis_title="Signal",
        yaxis_title="Probabilité",
        yaxis=dict(range=[0, 1], tickformat='.0%'),
        height=350,
        showlegend=False
    )
    return fig


st.title("Prédiction EUR/USD")
st.markdown("Entrez les données d'une bougie M15 pour obtenir un signal directionnel.")

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Données OHLCV")

    open_price = st.number_input("Open", min_value=0.0, value=1.0845, step=0.0001, format="%.4f")
    high_price = st.number_input("High", min_value=0.0, value=1.0855, step=0.0001, format="%.4f")
    low_price = st.number_input("Low", min_value=0.0, value=1.0840, step=0.0001, format="%.4f")
    close_price = st.number_input("Close", min_value=0.0, value=1.0850, step=0.0001, format="%.4f")
    tick_volume = st.number_input("Volume", min_value=0, value=1000, step=100)

with col2:
    st.subheader("Indicateurs externes (optionnels)")

    with st.expander("Indices boursiers"):
        spx_close = st.number_input("S&P 500 Close", value=None, step=10.0)
        spx_trend = st.number_input("S&P 500 Trend", value=None, step=0.01)
        risk_on = st.number_input("Risk-On Score", value=None, min_value=0.0, max_value=1.0, step=0.1)

    with st.expander("Matières premières"):
        gold_close = st.number_input("Gold Close", value=None, step=10.0)
        gold_trend = st.number_input("Gold Trend", value=None, step=0.01)
        safe_haven = st.number_input("Safe Haven Score", value=None, min_value=0.0, max_value=1.0, step=0.1)

    with st.expander("Dollar & Taux"):
        dxy_close = st.number_input("Dollar Index (DXY) Close", value=None, step=0.1)
        dxy_trend_1h = st.number_input("DXY Trend 1h", value=None, step=0.01)
        dxy_trend_4h = st.number_input("DXY Trend 4h", value=None, step=0.01)
        us10y_close = st.number_input("US 10Y Yield", value=None, step=0.1)
        us10y_trend = st.number_input("US 10Y Trend", value=None, step=0.01)

    with st.expander("Volatilité"):
        vix_close = st.number_input("VIX Close", value=None, step=1.0)
        vix_spike = st.number_input("VIX Spike", value=None, step=0.1)

valid_input = True
if high_price < low_price:
    st.error("Le prix High doit être supérieur au prix Low.")
    valid_input = False
if close_price < low_price or close_price > high_price:
    st.error("Le prix Close doit être entre Low et High.")
    valid_input = False
if open_price < low_price or open_price > high_price:
    st.error("Le prix Open doit être entre Low et High.")
    valid_input = False

st.divider()

predict_button = st.button("Prédire", type="primary", disabled=not valid_input)

if predict_button and valid_input:
    prediction_data = {
        "open": open_price, "high": high_price,
        "low": low_price, "close": close_price,
        "tick_volume": tick_volume
    }

    for key, val in [
        ("spx_close", spx_close), ("spx_trend", spx_trend), ("risk_on", risk_on),
        ("gold_close", gold_close), ("gold_trend", gold_trend), ("safe_haven", safe_haven),
        ("dxy_close", dxy_close), ("dxy_trend_1h", dxy_trend_1h), ("dxy_trend_4h", dxy_trend_4h),
        ("us10y_close", us10y_close), ("us10y_trend", us10y_trend),
        ("vix_close", vix_close), ("vix_spike", vix_spike),
    ]:
        if val is not None:
            prediction_data[key] = val

    with st.spinner("Calcul en cours..."):
        result = predict_single(prediction_data)

    if result:
        prediction_label = result["prediction_label"]
        confidence = result["confidence"]

        color = {"SHORT": "red", "LONG": "green"}.get(prediction_label, "orange")
        confidence_color = "green" if confidence > 0.7 else ("orange" if confidence > 0.5 else "red")

        col_r1, col_r2 = st.columns(2)

        with col_r1:
            st.markdown("### Signal")
            st.markdown(f"<h1 style='color: {color};'>{prediction_label}</h1>", unsafe_allow_html=True)

        with col_r2:
            st.markdown("### Confiance")
            st.markdown(f"<h1 style='color: {confidence_color};'>{confidence:.1%}</h1>", unsafe_allow_html=True)

        st.plotly_chart(plot_probabilities(result["probabilities"]), use_container_width=True)

        if prediction_label == "SHORT":
            st.error("""
**Signal de vente (SHORT)**

Le modèle prédit une baisse du prix EUR/USD.
Envisagez un stop-loss au-dessus du niveau High.
""")
        elif prediction_label == "LONG":
            st.success("""
**Signal d'achat (LONG)**

Le modèle prédit une hausse du prix EUR/USD.
Envisagez un stop-loss en dessous du niveau Low.
""")
        else:
            st.warning("""
**Signal neutre**

Pas de tendance claire détectée. Attendez une confirmation supplémentaire.
""")

        if confidence < 0.5:
            st.warning(f"Confiance faible ({confidence:.1%}) — utilisez ce signal avec prudence.")

st.divider()
st.caption("Disclaimer : Les prédictions ne constituent pas des conseils financiers. Le trading comporte des risques importants.")
