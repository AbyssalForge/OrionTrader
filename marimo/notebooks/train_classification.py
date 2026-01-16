import marimo

__generated_with = "0.19.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _(mo):
    mo.md("""
    # 🤖 OrionTrader - Entraînement Modèle de Classification

    Ce notebook entraîne un modèle de classification pour prédire les signaux de trading:
    - **BUY**: Achat
    - **SELL**: Vente
    - **HOLD**: Ne rien faire

    ## Pipeline
    1. Chargement des données depuis PostgreSQL
    2. Feature Engineering
    3. Création des labels
    4. Comparaison de modèles ML
    5. Évaluation du meilleur modèle
    """)
    return


@app.cell
def _():
    # Imports
    import pandas as pd
    import numpy as np
    from datetime import datetime
    import warnings
    import os

    warnings.filterwarnings('ignore')

    # ML
    from sklearn.model_selection import RandomizedSearchCV, cross_val_score
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.metrics import (
        classification_report, confusion_matrix, accuracy_score,
        precision_score, recall_score, f1_score
    )
    import joblib

    # Models
    from sklearn.linear_model import LogisticRegression
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.ensemble import (
        RandomForestClassifier, GradientBoostingClassifier,
        ExtraTreesClassifier
    )
    from sklearn.neighbors import KNeighborsClassifier
    from sklearn.naive_bayes import GaussianNB
    from xgboost import XGBClassifier
    from lightgbm import LGBMClassifier

    # Database
    import hvac
    import psycopg

    # MLflow
    import mlflow
    from mlflow.sklearn import log_model

    RANDOM_STATE = 42
    np.random.seed(RANDOM_STATE)

    print("✅ Imports terminés")
    return (
        DecisionTreeClassifier,
        ExtraTreesClassifier,
        GaussianNB,
        GradientBoostingClassifier,
        KNeighborsClassifier,
        LGBMClassifier,
        LabelEncoder,
        LogisticRegression,
        RANDOM_STATE,
        RandomForestClassifier,
        RandomizedSearchCV,
        StandardScaler,
        XGBClassifier,
        accuracy_score,
        classification_report,
        confusion_matrix,
        datetime,
        f1_score,
        hvac,
        joblib,
        log_model,
        mlflow,
        np,
        os,
        pd,
        precision_score,
        psycopg,
        recall_score,
    )


@app.cell
def _(mo):
    mo.md("""
    ## 📊 Étape 1: Chargement des données

    **Objectif**: Récupérer les données de trading depuis la base PostgreSQL.

    **Ce qui est fait**:
    1. **Connexion à Vault** : Récupération sécurisée des identifiants de la base de données (host, port, user, password)
    2. **Connexion PostgreSQL** : Établissement de la connexion avec `psycopg`
    3. **Requête SQL** : Jointure de 4 tables pour obtenir un dataset complet:
       - `market_snapshot_m15` : Snapshots du marché toutes les 15 minutes
       - `mt5_eurusd_m15` : Données OHLCV (Open, High, Low, Close, Volume) de MetaTrader 5
       - `yahoo_finance_daily` : Indicateurs macro (S&P500, Gold, DXY, VIX)
       - `documents_macro` : Données économiques (PIB, CPI eurozone)

    **Résultat**: Un DataFrame `df_raw` avec toutes les données brutes alignées temporellement.
    """)
    return


@app.cell
def _(hvac, os, pd, psycopg):
    # Configuration Vault
    VAULT_ADDR = os.getenv('VAULT_ADDR', 'http://vault:8200')
    VAULT_TOKEN = os.getenv('VAULT_TOKEN', '')

    print(f"🔐 Connexion à Vault: {VAULT_ADDR}")

    # Récupération des credentials
    client = hvac.Client(url=VAULT_ADDR, token=VAULT_TOKEN)

    try:
        secret = client.secrets.kv.v2.read_secret_version(path='Database')
        db_credentials = secret['data']['data']

        DB_HOST = db_credentials.get('POSTGRES_HOST', 'postgres')
        DB_PORT = db_credentials.get('POSTGRES_PORT', '5432')
        DB_NAME = db_credentials.get('POSTGRES_DB', 'postgres')
        DB_USER = db_credentials.get('POSTGRES_USER', 'postgres')
        DB_PASSWORD = db_credentials.get('POSTGRES_PASSWORD', 'postgres')

        print("✅ Credentials récupérés depuis Vault")
    except Exception as e:
        print(f"⚠️ Erreur Vault: {e}")
        DB_HOST = 'postgres'
        DB_PORT = '5432'
        DB_NAME = 'postgres'
        DB_USER = 'postgres'
        DB_PASSWORD = 'postgres'

    print(f"📊 Connexion: {DB_HOST}:{DB_PORT}/{DB_NAME}")

    # Connexion PostgreSQL
    conn = psycopg.connect(
        host=DB_HOST,
        port=int(DB_PORT),
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

    query = """
    SELECT
        s.time,
        m.open, m.high, m.low, m.close,
        m.tick_volume,
        m.close_diff, m.close_return, m.high_low_range,
        m.volatility_1h, m.volatility_4h,
        m.momentum_15m, m.momentum_1h, m.momentum_4h,
        m.body, m.upper_shadow, m.lower_shadow,
        y.spx_close, y.spx_trend, y.risk_on,
        y.gold_close, y.gold_trend, y.safe_haven,
        y.dxy_close, y.dxy_trend_1h, y.dxy_trend_4h, y.dxy_strength,
        y.vix_close, y.vix_level, y.vix_change, y.market_stress,
        d.eurozone_pib, d.pib_change, d.pib_growth,
        d.eurozone_cpi, d.cpi_change, d.inflation_pressure,
        d.event_impact_score,
        s.macro_micro_aligned,
        s.euro_strength_bias,
        s.regime_composite,
        s.volatility_regime,
        s.signal_confidence_score,
        s.signal_divergence_count,
        s.trend_strength_composite,
        s.event_window_active
    FROM market_snapshot_m15 s
    JOIN mt5_eurusd_m15 m ON s.mt5_time = m.time
    LEFT JOIN yahoo_finance_daily y ON s.yahoo_time = y.time
    LEFT JOIN documents_macro d ON s.docs_time = d.time
    ORDER BY s.time ASC
    """

    df_raw = pd.read_sql(query, conn)
    conn.close()

    print(f"✅ {len(df_raw):,} lignes chargées")
    print(f"📅 Période: {df_raw['time'].min()} → {df_raw['time'].max()}")
    return (df_raw,)


@app.cell
def _(df_raw, mo):
    mo.ui.table(df_raw.head(10))
    return


@app.cell
def _(mo):
    mo.md("""
    ## 🔥 Étape 1.5: Analyse de Corrélation (Heatmap)

    **Objectif**: Identifier les variables les plus pertinentes et leurs relations.

    **Ce qui est affiché**:
    1. **Matrice de corrélation** : Mesure la relation linéaire entre chaque paire de variables (-1 à +1)
    2. **Heatmap** : Visualisation colorée des corrélations

    **Comment lire la heatmap**:
    - **Rouge foncé (+1)** : Corrélation positive forte (quand l'une monte, l'autre monte)
    - **Bleu foncé (-1)** : Corrélation négative forte (quand l'une monte, l'autre descend)
    - **Blanc (0)** : Pas de corrélation linéaire

    **Utilité pour le ML**:
    - Éviter les features trop corrélées entre elles (redondance)
    - Identifier les features corrélées avec la cible (potentiellement prédictives)
    - Détecter les groupes de variables liées
    """)
    return


@app.cell
def _(df_raw, np):
    # Sélectionner uniquement les colonnes numériques
    numeric_cols = df_raw.select_dtypes(include=[np.number]).columns.tolist()

    # Exclure 'time' si présent
    numeric_cols = [c for c in numeric_cols if c != 'time']

    # Calculer la matrice de corrélation
    corr_matrix = df_raw[numeric_cols].corr()

    print(f"📊 Matrice de corrélation: {len(numeric_cols)} variables numériques")
    return (corr_matrix,)


@app.cell
def _(corr_matrix, np):
    import matplotlib.pyplot as plt_corr
    import seaborn as sns_corr

    # Créer la heatmap
    fig_heatmap, ax_heatmap = plt_corr.subplots(figsize=(16, 12))

    # Masque pour le triangle supérieur (éviter la redondance)
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool))

    # Heatmap avec seaborn
    sns_corr.heatmap(
        corr_matrix,
        mask=mask,
        annot=False,  # Pas d'annotations car trop de variables
        cmap='RdBu_r',  # Rouge-Blanc-Bleu
        center=0,
        vmin=-1,
        vmax=1,
        square=True,
        linewidths=0.5,
        cbar_kws={"shrink": 0.8, "label": "Corrélation"},
        ax=ax_heatmap
    )

    ax_heatmap.set_title('Matrice de Corrélation des Features', fontsize=14, fontweight='bold')
    plt_corr.xticks(rotation=45, ha='right', fontsize=8)
    plt_corr.yticks(fontsize=8)
    plt_corr.tight_layout()

    plt_corr.gca()
    return


@app.cell
def _(corr_matrix, mo, pd):
    # Afficher les corrélations les plus fortes (top 20)
    # Transformer la matrice en liste de paires
    corr_pairs = []
    for i in range(len(corr_matrix.columns)):
        for j in range(i+1, len(corr_matrix.columns)):
            corr_pairs.append({
                'Variable 1': corr_matrix.columns[i],
                'Variable 2': corr_matrix.columns[j],
                'Corrélation': corr_matrix.iloc[i, j]
            })

    corr_df = pd.DataFrame(corr_pairs)
    corr_df['Abs_Corr'] = corr_df['Corrélation'].abs()
    corr_df = corr_df.sort_values('Abs_Corr', ascending=False)

    mo.md("### 🔝 Top 20 des corrélations les plus fortes")
    return (corr_df,)


@app.cell
def _(corr_df, mo):
    # Afficher le top 20
    top_corr = corr_df.head(20)[['Variable 1', 'Variable 2', 'Corrélation']].copy()
    top_corr['Corrélation'] = top_corr['Corrélation'].round(3)
    mo.ui.table(top_corr)
    return


@app.cell
def _(mo):
    mo.md("""
    ## 🔧 Étape 2: Feature Engineering

    **Objectif**: Créer de nouvelles variables (features) à partir des données brutes pour améliorer la capacité prédictive du modèle.

    **Ce qui est fait**:

    | Feature | Description | Utilité |
    |---------|-------------|---------|
    | `hour`, `day_of_week` | Heure et jour de la semaine | Capturer les patterns temporels (ex: volatilité à l'ouverture des marchés) |
    | `ma_5`, `ma_10`, `ma_20`, `ma_50` | Moyennes mobiles | Identifier la tendance à court/moyen/long terme |
    | `dist_ma_5`, `dist_ma_20` | Distance du prix aux MA (%) | Mesurer si le prix est suracheté/survendu par rapport à sa moyenne |
    | `trend_short`, `trend_long` | MA5 > MA10, MA20 > MA50 | Signal binaire de tendance haussière/baissière |
    | `rsi` | Relative Strength Index (14 périodes) | Indicateur de momentum (0-100), >70 = suracheté, <30 = survendu |
    | `bb_upper`, `bb_lower`, `bb_position` | Bandes de Bollinger | Mesurer la volatilité et position du prix dans son range |
    | `close_return_lag_1/2/3` | Rendements passés | Capturer l'inertie du marché (momentum) |
    | `momentum_1h_lag_1/2/3` | Momentum passé | Continuité des mouvements de prix |

    **Résultat**: DataFrame `df_fe` enrichi avec ~20 nouvelles features techniques.
    """)
    return


@app.cell
def _(df_raw, pd):
    df_fe = df_raw.copy()

    # Features temporelles
    df_fe['hour'] = pd.to_datetime(df_fe['time']).dt.hour
    df_fe['day_of_week'] = pd.to_datetime(df_fe['time']).dt.dayofweek

    # Moyennes mobiles
    for window in [5, 10, 20, 50]:
        df_fe[f'ma_{window}'] = df_fe['close'].rolling(window).mean()

    # Distance aux MA
    df_fe['dist_ma_5'] = (df_fe['close'] - df_fe['ma_5']) / df_fe['ma_5'] * 100
    df_fe['dist_ma_20'] = (df_fe['close'] - df_fe['ma_20']) / df_fe['ma_20'] * 100

    # Trends
    df_fe['trend_short'] = (df_fe['ma_5'] > df_fe['ma_10']).astype(int)
    df_fe['trend_long'] = (df_fe['ma_20'] > df_fe['ma_50']).astype(int)

    # RSI
    delta = df_fe['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df_fe['rsi'] = 100 - (100 / (1 + rs))

    # Bollinger Bands
    df_fe['bb_mid'] = df_fe['close'].rolling(20).mean()
    df_fe['bb_std'] = df_fe['close'].rolling(20).std()
    df_fe['bb_upper'] = df_fe['bb_mid'] + (2 * df_fe['bb_std'])
    df_fe['bb_lower'] = df_fe['bb_mid'] - (2 * df_fe['bb_std'])
    df_fe['bb_position'] = (df_fe['close'] - df_fe['bb_lower']) / (df_fe['bb_upper'] - df_fe['bb_lower'])

    # Lag features
    for lag in [1, 2, 3]:
        df_fe[f'close_return_lag_{lag}'] = df_fe['close_return'].shift(lag)
        df_fe[f'momentum_1h_lag_{lag}'] = df_fe['momentum_1h'].shift(lag)

    new_features = len(df_fe.columns) - len(df_raw.columns)
    print(f"✅ {new_features} nouvelles features créées")
    print(f"📊 Total: {len(df_fe.columns)} colonnes")
    return (df_fe,)


@app.cell
def _(mo):
    mo.md("""
    ## 🎯 Étape 3: Création des Labels (BUY/SELL/HOLD)

    **Objectif**: Définir ce que le modèle doit prédire - la variable cible (label).

    **Ce qui est fait**:

    1. **Calcul du rendement futur**: Pour chaque bougie, on calcule le % de variation du prix dans les N prochaines bougies
       ```
       future_return = (prix_futur - prix_actuel) / prix_actuel × 100
       ```

    2. **Attribution du label** selon le rendement futur:
       - **BUY** : Si `future_return > seuil` → Le prix va monter, il faut acheter
       - **SELL** : Si `future_return < -seuil` → Le prix va baisser, il faut vendre
       - **HOLD** : Si `-seuil ≤ future_return ≤ seuil` → Pas de mouvement significatif, ne rien faire

    **Paramètres ajustables** (sliders ci-dessous):
    - **Fenêtre forward** : Nombre de bougies M15 à regarder dans le futur (16 = 4 heures)
    - **Seuil (%)** : Mouvement minimum pour déclencher un signal (0.05% par défaut)

    **⚠️ Attention**: Un seuil trop bas = trop de signaux (bruit), un seuil trop haut = pas assez de signaux (manque d'opportunités)
    """)
    return


@app.cell
def _(mo):
    # Paramètres interactifs
    forward_window = mo.ui.slider(4, 32, value=16, label="Fenêtre forward (bougies M15)")
    threshold_pct = mo.ui.slider(0.01, 0.2, step=0.01, value=0.05, label="Seuil (%)")

    mo.hstack([forward_window, threshold_pct])
    return forward_window, threshold_pct


@app.cell
def _(df_fe, forward_window, pd, threshold_pct):
    df_labeled = df_fe.copy()

    # Return futur
    df_labeled['future_return'] = (
        (df_labeled['close'].shift(-forward_window.value) - df_labeled['close'])
        / df_labeled['close'] * 100
    )

    # Labels
    def assign_label(future_return, threshold=threshold_pct.value):
        if pd.isna(future_return):
            return None
        elif future_return > threshold:
            return 'BUY'
        elif future_return < -threshold:
            return 'SELL'
        else:
            return 'HOLD'

    df_labeled['label'] = df_labeled['future_return'].apply(assign_label)
    df_labeled = df_labeled.dropna(subset=['label'])

    print(f"✅ Labels créés: {len(df_labeled):,} lignes")
    print(f"\n📊 Distribution:")
    label_counts = df_labeled['label'].value_counts()
    for lbl, cnt in label_counts.items():
        pct = cnt / len(df_labeled) * 100
        print(f"   {lbl}: {cnt:,} ({pct:.1f}%)")
    return (df_labeled,)


@app.cell
def _(mo):
    mo.md("""
    ## 🎯 Étape 3.5: Sélection des Features (Corrélation avec la cible)

    **Objectif**: Identifier et filtrer les features qui n'ont aucune corrélation avec la variable cible.

    **Ce qui est fait**:
    1. **Encodage temporaire du label** : BUY=1, HOLD=0, SELL=-1 (pour calculer la corrélation)
    2. **Calcul de la corrélation** de chaque feature avec le label encodé
    3. **Filtrage** : Retirer les features avec |corrélation| < seuil

    **Pourquoi filtrer ?**
    - Les features sans corrélation avec la cible = **bruit** pour le modèle
    - Réduire le nombre de features = modèle plus rapide et moins d'overfitting
    - Garder uniquement les features **potentiellement prédictives**

    **⚠️ Note**: Une corrélation faible ne signifie pas toujours que la feature est inutile (relations non-linéaires), mais c'est un bon premier filtre.
    """)
    return


@app.cell
def _(mo):
    # Slider pour le seuil de corrélation minimum
    corr_threshold = mo.ui.slider(0.0, 0.1, step=0.005, value=0.01, label="Seuil de corrélation minimum (|corr|)")
    corr_threshold
    return (corr_threshold,)


@app.cell
def _(corr_threshold, df_labeled, pd):
    # Encoder le label pour calculer la corrélation
    label_encoding_corr = {'BUY': 1, 'HOLD': 0, 'SELL': -1}
    df_corr_analysis = df_labeled.copy()
    df_corr_analysis['label_encoded'] = df_corr_analysis['label'].map(label_encoding_corr)

    # Sélectionner les colonnes numériques (exclure time, label, future_return)
    exclude_corr = ['time', 'label', 'future_return', 'label_encoded']
    numeric_features = [c for c in df_corr_analysis.columns if c not in exclude_corr]
    numeric_features = [c for c in numeric_features if df_corr_analysis[c].dtype in ['int64', 'float64', 'int32', 'float32']]

    # Calculer la corrélation de chaque feature avec le label
    correlations_with_target = {}
    for feat in numeric_features:
        corr_val = df_corr_analysis[feat].corr(df_corr_analysis['label_encoded'])
        if not pd.isna(corr_val):
            correlations_with_target[feat] = corr_val

    # Créer un DataFrame pour affichage
    corr_target_df = pd.DataFrame({
        'Feature': list(correlations_with_target.keys()),
        'Corrélation': list(correlations_with_target.values())
    })
    corr_target_df['Abs_Corr'] = corr_target_df['Corrélation'].abs()
    corr_target_df = corr_target_df.sort_values('Abs_Corr', ascending=False)

    # Filtrer selon le seuil
    threshold_val = corr_threshold.value
    features_to_keep = corr_target_df[corr_target_df['Abs_Corr'] >= threshold_val]['Feature'].tolist()
    features_removed = corr_target_df[corr_target_df['Abs_Corr'] < threshold_val]['Feature'].tolist()

    print(f"📊 Analyse de corrélation avec la cible (label)")
    print(f"   Seuil: |corrélation| >= {threshold_val}")
    print(f"   ✅ Features gardées: {len(features_to_keep)}")
    print(f"   ❌ Features retirées: {len(features_removed)}")
    return corr_target_df, features_to_keep


@app.cell
def _(corr_target_df, corr_threshold, mo):
    # Afficher le tableau des corrélations avec indication visuelle
    display_corr = corr_target_df.copy()
    display_corr['Corrélation'] = display_corr['Corrélation'].round(4)
    display_corr['Statut'] = display_corr['Abs_Corr'].apply(
        lambda x: '✅ Gardée' if x >= corr_threshold.value else '❌ Retirée'
    )
    display_corr = display_corr[['Feature', 'Corrélation', 'Statut']]

    mo.md("### 📋 Corrélation des features avec le label")
    return (display_corr,)


@app.cell
def _(display_corr, mo):
    mo.ui.table(display_corr)
    return


@app.cell
def _(corr_target_df, corr_threshold):
    import matplotlib.pyplot as plt_feat

    # Graphique en barres des corrélations
    fig_corr_bar, ax_corr_bar = plt_feat.subplots(figsize=(12, max(6, len(corr_target_df) * 0.25)))

    # Trier par corrélation
    sorted_corr = corr_target_df.sort_values('Corrélation')

    # Couleurs selon le seuil
    colors = ['green' if abs(c) >= corr_threshold.value else 'red' for c in sorted_corr['Corrélation']]

    ax_corr_bar.barh(sorted_corr['Feature'], sorted_corr['Corrélation'], color=colors, alpha=0.7)
    ax_corr_bar.axvline(x=0, color='black', linewidth=0.5)
    ax_corr_bar.axvline(x=corr_threshold.value, color='gray', linestyle='--', alpha=0.5, label=f'Seuil +{corr_threshold.value}')
    ax_corr_bar.axvline(x=-corr_threshold.value, color='gray', linestyle='--', alpha=0.5, label=f'Seuil -{corr_threshold.value}')

    ax_corr_bar.set_xlabel('Corrélation avec le label')
    ax_corr_bar.set_title('Corrélation des Features avec la Cible (BUY=1, HOLD=0, SELL=-1)')
    ax_corr_bar.legend()

    plt_feat.tight_layout()
    plt_feat.gca()
    return


@app.cell
def _(mo):
    mo.md("""
    ### 🔥 Heatmap avec corrélation Label en première colonne
    """)
    return


@app.cell
def _(corr_threshold, df_labeled):
    import matplotlib.pyplot as plt_heat2
    import seaborn as sns_heat2

    # Encoder le label pour la heatmap
    label_map_heat = {'BUY': 1, 'HOLD': 0, 'SELL': -1}
    df_heat = df_labeled.copy()
    df_heat['Label'] = df_heat['label'].map(label_map_heat)

    # Sélectionner colonnes numériques
    exclude_heat = ['time', 'label', 'future_return']
    heat_cols = [c for c in df_heat.columns if c not in exclude_heat]
    heat_cols = [c for c in heat_cols if df_heat[c].dtype in ['int64', 'float64', 'int32', 'float32']]

    # Mettre 'Label' en premier
    if 'Label' in heat_cols:
        heat_cols.remove('Label')
    heat_cols = ['Label'] + heat_cols

    # Calculer la matrice de corrélation
    corr_with_label = df_heat[heat_cols].corr()

    # Extraire uniquement la colonne Label (corrélation avec toutes les autres)
    label_corr = corr_with_label['Label'].drop('Label').sort_values(key=abs, ascending=False)

    # Filtrer selon le seuil
    label_corr_filtered = label_corr[abs(label_corr) >= corr_threshold.value]

    # Créer une heatmap en 1 colonne (Label vs Features)
    fig_heat2, ax_heat2 = plt_heat2.subplots(figsize=(4, max(8, len(label_corr_filtered) * 0.35)))

    # Données pour la heatmap (1 colonne)
    heat_data = label_corr_filtered.values.reshape(-1, 1)

    sns_heat2.heatmap(
        heat_data,
        annot=True,
        fmt='.3f',
        cmap='RdBu_r',
        center=0,
        vmin=-1,
        vmax=1,
        xticklabels=['Label'],
        yticklabels=label_corr_filtered.index,
        cbar_kws={"shrink": 0.8, "label": "Corrélation"},
        ax=ax_heat2
    )

    ax_heat2.set_title(f'Corrélation avec Label\n(seuil >= {corr_threshold.value})', fontsize=12, fontweight='bold')
    plt_heat2.yticks(fontsize=9)
    plt_heat2.tight_layout()

    plt_heat2.gca()
    return


@app.cell
def _(mo):
    mo.md("""
    ## 📋 Étape 4: Préparation des données ML

    **Objectif**: Transformer les données pour qu'elles soient utilisables par les algorithmes de Machine Learning.

    **Ce qui est fait**:

    1. **Sélection des features**:
       - On garde uniquement les colonnes numériques
       - On exclut: `time` (date), `future_return` (triche!), `label` (c'est ce qu'on prédit)

    2. **Encodage des variables catégorielles**:
       - `regime_composite` et `volatility_regime` sont des textes → convertis en nombres (0, 1, 2...)
       - Les labels BUY/SELL/HOLD → convertis en 0/1/2 (requis par XGBoost/LightGBM)

    3. **Nettoyage des NaN**:
       - Suppression des lignes contenant des valeurs manquantes
       - Les premières lignes ont des NaN (car les MA ont besoin d'historique)

    4. **Split Train/Test (80/20)**:
       - **Chronologique** : Les 80% les plus anciens pour l'entraînement, les 20% récents pour le test
       - ⚠️ Pas de shuffle aléatoire ! (sinon on "tricherait" en utilisant le futur pour prédire le passé)

    5. **Standardisation (StandardScaler)**:
       - Centre les données (moyenne = 0) et les met à la même échelle (écart-type = 1)
       - Essentiel pour certains algorithmes (Régression Logistique, KNN, SVM)

    **Résultat**: `X_train_scaled`, `X_test_scaled` (features) et `y_train`, `y_test` (labels)
    """)
    return


@app.cell
def _(LabelEncoder, StandardScaler, df_labeled, features_to_keep):
    # Sélection des features (utiliser celles filtrées par corrélation)
    categorical_cols = ['regime_composite', 'volatility_regime']

    # Encoder catégorielles d'abord
    df_ml = df_labeled.copy()
    for col in categorical_cols:
        if col in df_ml.columns:
            le = LabelEncoder()
            df_ml[col + '_encoded'] = le.fit_transform(df_ml[col].astype(str))

    # Utiliser les features filtrées par corrélation (étape 3.5)
    # Garder uniquement celles qui existent dans df_ml et qui sont numériques
    feature_cols = [c for c in features_to_keep if c in df_ml.columns]
    feature_cols = [c for c in feature_cols if df_ml[c].dtype in ['int64', 'float64', 'int32', 'float32']]

    # Garder les colonnes features + label + close (pour backtesting) + time
    cols_to_keep_ml = feature_cols + ['label', 'close', 'time']
    df_clean = df_ml[[c for c in cols_to_keep_ml if c in df_ml.columns]].copy()

    # Supprimer toutes les lignes avec NaN dans les features
    rows_before = len(df_clean)
    df_clean = df_clean.dropna(subset=feature_cols)
    rows_after = len(df_clean)

    print(f"✅ Données nettoyées: {rows_after:,} lignes (supprimé {rows_before - rows_after:,} lignes avec NaN)")
    print(f"📊 Features sélectionnées (après filtrage corrélation): {len(feature_cols)}")

    # X et y
    X = df_clean[feature_cols]
    y_raw = df_clean['label']

    # Encoder les labels (BUY/SELL/HOLD -> 0/1/2) pour XGBoost/LightGBM
    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(y_raw)
    label_mapping = dict(zip(label_encoder.classes_, label_encoder.transform(label_encoder.classes_)))
    print(f"🏷️ Mapping labels: {label_mapping}")

    # Vérification finale - aucun NaN ne doit rester
    nan_count = X.isna().sum().sum()
    print(f"🔍 Vérification NaN dans X: {nan_count}")

    # Split chronologique (80/20)
    split_idx = int(len(X) * 0.8)
    X_train = X.iloc[:split_idx]
    X_test = X.iloc[split_idx:]
    y_train = y[:split_idx]
    y_test = y[split_idx:]

    # Garder df_clean pour le backtesting (avec close et time)
    df_backtest = df_clean.iloc[split_idx:].copy()

    print(f"\n📊 Train: {len(X_train):,} ({len(X_train)/len(X)*100:.1f}%)")
    print(f"📊 Test: {len(X_test):,} ({len(X_test)/len(X)*100:.1f}%)")

    # Standardisation
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    print("✅ Features standardisées")
    return (
        X_test_scaled,
        X_train_scaled,
        df_backtest,
        label_encoder,
        scaler,
        y_test,
        y_train,
    )


@app.cell
def _(mo):
    mo.md("""
    ## 🤖 Étape 5: Comparaison des Modèles

    **Objectif**: Tester plusieurs algorithmes de Machine Learning et trouver le meilleur.

    **Modèles testés**:

    | Modèle | Type | Points forts | Points faibles |
    |--------|------|--------------|----------------|
    | **Logistic Regression** | Linéaire | Rapide, interprétable | Limité si relations non-linéaires |
    | **Decision Tree** | Arbre | Interprétable, pas de scaling requis | Overfitting facile |
    | **Random Forest** | Ensemble (Bagging) | Robuste, gère bien le bruit | Lent, boîte noire |
    | **Gradient Boosting** | Ensemble (Boosting) | Très performant | Lent à entraîner |
    | **XGBoost** | Ensemble (Boosting) | État de l'art, rapide | Beaucoup d'hyperparamètres |
    | **LightGBM** | Ensemble (Boosting) | Très rapide, performant | Peut overfitter |
    | **Extra Trees** | Ensemble (Bagging) | Plus rapide que RF | Moins précis parfois |
    | **KNN** | Distance | Simple, pas d'entraînement | Lent en prédiction, sensible au scaling |
    | **Naive Bayes** | Probabiliste | Très rapide | Assume indépendance des features |

    **Métriques calculées**:
    - **Accuracy** : % de prédictions correctes (peut être trompeur si classes déséquilibrées)
    - **Precision** : Parmi les prédictions positives, combien sont correctes ?
    - **Recall** : Parmi les vrais positifs, combien ont été trouvés ?
    - **F1-Score** : Moyenne harmonique de Precision et Recall (métrique principale)

    **Résultat**: Tableau comparatif trié par F1-Score décroissant.
    """)
    return


@app.cell
def _(
    DecisionTreeClassifier,
    ExtraTreesClassifier,
    GaussianNB,
    GradientBoostingClassifier,
    KNeighborsClassifier,
    LGBMClassifier,
    LogisticRegression,
    RANDOM_STATE,
    RandomForestClassifier,
    XGBClassifier,
    X_test_scaled,
    X_train_scaled,
    accuracy_score,
    datetime,
    f1_score,
    pd,
    precision_score,
    recall_score,
    y_test,
    y_train,
):
    models = {
        'Logistic Regression': LogisticRegression(random_state=RANDOM_STATE, max_iter=1000),
        'Decision Tree': DecisionTreeClassifier(random_state=RANDOM_STATE),
        'Random Forest': RandomForestClassifier(random_state=RANDOM_STATE, n_estimators=100),
        'Gradient Boosting': GradientBoostingClassifier(random_state=RANDOM_STATE, n_estimators=100),
        'XGBoost': XGBClassifier(random_state=RANDOM_STATE, n_estimators=100, eval_metric='mlogloss', verbosity=0),
        'LightGBM': LGBMClassifier(random_state=RANDOM_STATE, n_estimators=100, verbose=-1),
        'Extra Trees': ExtraTreesClassifier(random_state=RANDOM_STATE, n_estimators=100),
        'KNN': KNeighborsClassifier(n_neighbors=5),
        'Naive Bayes': GaussianNB()
    }

    results = []

    print(f"⏳ Entraînement de {len(models)} modèles...\n")

    for name, model in models.items():
        print(f"   {name}...", end=" ")

        t_start = datetime.now()
        model.fit(X_train_scaled, y_train)
        train_time = (datetime.now() - t_start).total_seconds()

        y_pred = model.predict(X_test_scaled)

        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, average='weighted', zero_division=0)
        recall = recall_score(y_test, y_pred, average='weighted', zero_division=0)
        f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)

        results.append({
            'Model': name,
            'Accuracy': round(accuracy, 4),
            'Precision': round(precision, 4),
            'Recall': round(recall, 4),
            'F1-Score': round(f1, 4),
            'Time (s)': round(train_time, 2),
            'trained_model': model
        })

        print(f"✓ F1: {f1:.4f}")

    results_df = pd.DataFrame(results).sort_values('F1-Score', ascending=False)
    print("\n✅ Entraînement terminé!")
    return (results_df,)


@app.cell
def _(mo, results_df):
    # Affichage des résultats
    display_df = results_df[['Model', 'Accuracy', 'Precision', 'Recall', 'F1-Score', 'Time (s)']]
    mo.ui.table(display_df)
    return


@app.cell
def _(mo):
    mo.md("""
    ## 🏆 Étape 6: Évaluation du Meilleur Modèle

    **Objectif**: Analyser en détail les performances du modèle gagnant.

    **Ce qui est affiché**:

    1. **Classification Report**:
       - Precision, Recall, F1-Score **par classe** (BUY, SELL, HOLD)
       - Permet de voir si le modèle est meilleur sur certaines classes que d'autres
       - `support` = nombre d'exemples de chaque classe dans le test set

    2. **Matrice de Confusion**:
       - Tableau croisé: lignes = vraies valeurs, colonnes = prédictions
       - Diagonale = prédictions correctes
       - Hors diagonale = erreurs

       Exemple de lecture:
       ```
                 BUY  HOLD  SELL
       BUY       50    10     5    → Sur 65 vrais BUY, 50 bien prédits
       HOLD      8     80    12    → Sur 100 vrais HOLD, 80 bien prédits
       SELL      3     15    47    → Sur 65 vrais SELL, 47 bien prédits
       ```

    **Interprétation pour le trading**:
    - Un bon modèle minimise les **faux BUY quand c'est SELL** (perte d'argent!)
    - HOLD mal prédit est moins grave (opportunité manquée, pas de perte)
    """)
    return


@app.cell
def _(X_test_scaled, mo, results_df):
    best_row = results_df.iloc[0]
    best_model_name = best_row['Model']
    best_model = best_row['trained_model']

    y_pred_best = best_model.predict(X_test_scaled)

    mo.md(f"""
    ### 🥇 Meilleur modèle: **{best_model_name}**

    | Métrique | Valeur |
    |----------|--------|
    | Accuracy | {best_row['Accuracy']:.4f} |
    | Precision | {best_row['Precision']:.4f} |
    | Recall | {best_row['Recall']:.4f} |
    | F1-Score | {best_row['F1-Score']:.4f} |
    """)
    return (y_pred_best,)


@app.cell
def _(classification_report, label_encoder, y_pred_best, y_test):
    # Décoder les labels pour l'affichage
    y_test_labels = label_encoder.inverse_transform(y_test)
    y_pred_labels = label_encoder.inverse_transform(y_pred_best)

    print("📋 Classification Report:\n")
    print(classification_report(y_test_labels, y_pred_labels))
    return y_pred_labels, y_test_labels


@app.cell
def _(confusion_matrix, mo, np, pd, y_pred_labels, y_test_labels):
    # Matrice de confusion avec labels décodés
    labels = sorted(np.unique(y_test_labels))
    cm = confusion_matrix(y_test_labels, y_pred_labels, labels=labels)
    cm_df = pd.DataFrame(cm, index=labels, columns=labels)

    mo.md("### 📊 Matrice de Confusion")
    return (cm_df,)


@app.cell
def _(cm_df, mo):
    mo.ui.table(cm_df)
    return


@app.cell
def _(mo):
    mo.md("""
    ## 🔧 Étape 7: Optimisation des Hyperparamètres

    **Objectif**: Améliorer les performances du meilleur modèle en trouvant les paramètres optimaux.

    **Ce qui est fait**:

    1. **RandomizedSearchCV**: Recherche aléatoire dans l'espace des hyperparamètres
       - Plus rapide que GridSearchCV (qui teste toutes les combinaisons)
       - Teste `n_iter` combinaisons aléatoires

    2. **Cross-Validation (3-fold)**: Pour chaque combinaison de paramètres:
       - Divise les données d'entraînement en 3 parties
       - Entraîne sur 2 parties, valide sur la 3ème
       - Répète 3 fois et fait la moyenne → score plus robuste

    3. **Hyperparamètres testés** (selon le modèle):
       - `n_estimators`: Nombre d'arbres (100, 200, 300)
       - `max_depth`: Profondeur max des arbres (5, 10, 20, None)
       - `learning_rate`: Vitesse d'apprentissage (0.01, 0.1, 0.3)
       - `min_samples_split`, `min_samples_leaf`: Contrôle de l'overfitting

    **⚠️ Note**: Cette étape peut prendre plusieurs minutes selon la taille des données.
    """)
    return


@app.cell
def _(
    RANDOM_STATE,
    RandomizedSearchCV,
    X_test_scaled,
    X_train_scaled,
    datetime,
    f1_score,
    results_df,
    y_test,
    y_train,
):
    # Récupérer le meilleur modèle
    best_model_name_opt = results_df.iloc[0]['Model']
    best_model_base = results_df.iloc[0]['trained_model']

    print(f"🔧 Optimisation de: {best_model_name_opt}")
    print("⏳ Recherche des meilleurs hyperparamètres...\n")

    # Définir les grilles de paramètres selon le modèle
    param_grids = {
        'Random Forest': {
            'n_estimators': [100, 200, 300],
            'max_depth': [5, 10, 20, None],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4]
        },
        'XGBoost': {
            'n_estimators': [100, 200, 300],
            'max_depth': [3, 5, 7, 10],
            'learning_rate': [0.01, 0.05, 0.1, 0.3],
            'subsample': [0.8, 0.9, 1.0],
            'colsample_bytree': [0.8, 0.9, 1.0]
        },
        'LightGBM': {
            'n_estimators': [100, 200, 300],
            'max_depth': [3, 5, 7, 10],
            'learning_rate': [0.01, 0.05, 0.1, 0.3],
            'num_leaves': [20, 31, 50],
            'subsample': [0.8, 0.9, 1.0]
        },
        'Gradient Boosting': {
            'n_estimators': [100, 200, 300],
            'max_depth': [3, 5, 7],
            'learning_rate': [0.01, 0.05, 0.1],
            'min_samples_split': [2, 5, 10]
        },
        'Extra Trees': {
            'n_estimators': [100, 200, 300],
            'max_depth': [5, 10, 20, None],
            'min_samples_split': [2, 5, 10]
        }
    }

    # Si le modèle a une grille définie, optimiser
    if best_model_name_opt in param_grids:
        param_grid = param_grids[best_model_name_opt]

        t_opt_start = datetime.now()

        random_search = RandomizedSearchCV(
            best_model_base.__class__(**{'random_state': RANDOM_STATE, 'verbose': 0} if 'verbose' in best_model_base.get_params() else {'random_state': RANDOM_STATE}),
            param_distributions=param_grid,
            n_iter=20,
            cv=3,
            scoring='f1_weighted',
            random_state=RANDOM_STATE,
            n_jobs=-1,
            verbose=1
        )

        random_search.fit(X_train_scaled, y_train)

        optimization_time = (datetime.now() - t_opt_start).total_seconds()

        best_model_optimized = random_search.best_estimator_
        best_params = random_search.best_params_

        # Évaluer le modèle optimisé
        y_pred_opt = best_model_optimized.predict(X_test_scaled)

        f1_before = results_df.iloc[0]['F1-Score']
        f1_after = f1_score(y_test, y_pred_opt, average='weighted')
        improvement = (f1_after - f1_before) / f1_before * 100

        print(f"\n✅ Optimisation terminée en {optimization_time:.1f}s")
        print(f"\n📊 Meilleurs paramètres trouvés:")
        for param, value in best_params.items():
            print(f"   - {param}: {value}")

        print(f"\n📈 Amélioration:")
        print(f"   F1-Score avant: {f1_before:.4f}")
        print(f"   F1-Score après: {f1_after:.4f}")
        print(f"   Gain: {improvement:+.2f}%")
    else:
        print(f"⚠️ Pas de grille de paramètres définie pour {best_model_name_opt}")
        best_model_optimized = best_model_base
        best_params = {}
    return best_model_optimized, best_params


@app.cell
def _(mo):
    mo.md("""
    ## 💾 Étape 8: Sauvegarde du Modèle sur MLflow

    **Objectif**: Sauvegarder le modèle optimisé sur MLflow pour versioning et déploiement.

    **Ce qui est sauvegardé sur MLflow**:
    1. **Le modèle** : L'algorithme entraîné avec ses paramètres optimaux
    2. **Les métriques** : Accuracy, Precision, Recall, F1-Score
    3. **Les hyperparamètres** : Paramètres optimisés du modèle
    4. **Les artifacts** : Scaler et LabelEncoder pour la prédiction

    **Utilisation future** (depuis MLflow):
    ```python
    import mlflow
    model = mlflow.sklearn.load_model("runs:/<run_id>/model")
    ```

    👇 **Cliquez sur le bouton ci-dessous pour sauvegarder le modèle sur MLflow**
    """)
    return


@app.cell
def _(mo):
    # Bouton de sauvegarde
    save_button = mo.ui.button(label="💾 Sauvegarder sur MLflow", kind="success")
    save_button
    return (save_button,)


@app.cell
def _(
    best_model_optimized,
    best_params,
    datetime,
    joblib,
    label_encoder,
    log_model,
    mlflow,
    mo,
    os,
    results_df,
    save_button,
    scaler,
):
    import tempfile

    # Variable pour stocker le résultat
    save_result = {"status": None, "message": "", "run_id": None}

    # Ne s'exécute que si le bouton est cliqué
    if save_button.value > 0:
        try:
            # Configuration MLflow
            mlflow.set_tracking_uri("http://mlflow:5000")
            mlflow.set_experiment("OrionTrader_Classification")

            model_name = results_df.iloc[0]['Model']

            with mlflow.start_run(run_name=f"{model_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):
                # Log des métriques
                mlflow.log_metric("accuracy", float(results_df.iloc[0]['Accuracy']))
                mlflow.log_metric("precision", float(results_df.iloc[0]['Precision']))
                mlflow.log_metric("recall", float(results_df.iloc[0]['Recall']))
                mlflow.log_metric("f1_score", float(results_df.iloc[0]['F1-Score']))

                # Log des hyperparamètres
                for param_name, param_value in best_params.items():
                    mlflow.log_param(param_name, param_value)
                mlflow.log_param("model_type", model_name)

                # Log du modèle
                log_model(best_model_optimized, "model")

                # Sauvegarder scaler et label_encoder comme artifacts
                with tempfile.TemporaryDirectory() as tmpdir:
                    scaler_path = os.path.join(tmpdir, "scaler.joblib")
                    encoder_path = os.path.join(tmpdir, "label_encoder.joblib")

                    joblib.dump(scaler, scaler_path)
                    joblib.dump(label_encoder, encoder_path)

                    mlflow.log_artifact(scaler_path, "preprocessing")
                    mlflow.log_artifact(encoder_path, "preprocessing")

                # Récupérer le run_id
                run_id = mlflow.active_run().info.run_id

            save_result = {
                "status": "success",
                "message": f"Modèle sauvegardé avec succès!",
                "run_id": run_id
            }

        except Exception as e:
            save_result = {
                "status": "error",
                "message": f"Erreur: {str(e)}",
                "run_id": None
            }

    # Affichage du résultat
    if save_result["status"] == "success":
        mo.md(f"""
        ✅ **{save_result['message']}**

        - **Run ID**: `{save_result['run_id']}`
        - **MLflow UI**: [http://localhost:5000](http://localhost:5000)

        Pour charger le modèle:
        ```python
        import mlflow
        model = mlflow.sklearn.load_model("runs:/{save_result['run_id']}/model")
        ```
        """)
    elif save_result["status"] == "error":
        mo.md(f"""
        ❌ **Erreur lors de la sauvegarde**

        {save_result['message']}

        Vérifiez que le service MLflow est démarré (`docker-compose up mlflow`).
        """)
    else:
        mo.md("⏳ *Cliquez sur le bouton ci-dessus pour sauvegarder le modèle*")
    return


@app.cell
def _(mo):
    mo.md("""
    ## 📈 Étape 9: Backtesting

    **Objectif**: Simuler l'utilisation du modèle sur des données historiques pour évaluer la rentabilité.

    **Ce qui est fait**:

    1. **Simulation de trades** sur le jeu de test:
       - Quand le modèle prédit **BUY** → On achète (position longue)
       - Quand le modèle prédit **SELL** → On vend (position courte)
       - Quand le modèle prédit **HOLD** → On ne fait rien

    2. **Calcul du P&L (Profit & Loss)**:
       - Pour chaque trade, on calcule le rendement réel
       - P&L = Σ (rendement réel × direction du trade)

    3. **Métriques de trading**:
       - **Total Return**: Rendement total cumulé
       - **Win Rate**: % de trades gagnants
       - **Sharpe Ratio**: Rendement ajusté au risque
       - **Max Drawdown**: Perte maximale depuis un pic

    **⚠️ Attention**:
    - Ce backtest est simplifié (pas de frais, pas de slippage)
    - Les performances passées ne garantissent pas les performances futures
    """)
    return


@app.cell
def _(X_test_scaled, best_model_optimized, df_backtest, label_encoder, np, pd):
    # Utiliser df_backtest qui a déjà été créé avec le bon split et contient 'close'
    df_test = df_backtest.copy()

    # Prédictions du modèle optimisé
    y_pred_backtest = best_model_optimized.predict(X_test_scaled)
    y_pred_labels_bt = label_encoder.inverse_transform(y_pred_backtest)

    # Ajouter les prédictions au DataFrame (même taille car df_backtest = df_clean[split_idx:])
    df_test = df_test.reset_index(drop=True)
    df_test['prediction'] = y_pred_labels_bt

    # Calculer le rendement réel pour chaque période
    df_test['actual_return'] = df_test['close'].pct_change().shift(-1) * 100

    # Calculer le P&L selon la prédiction
    def calculate_pnl(row):
        if pd.isna(row['actual_return']):
            return 0
        if row['prediction'] == 'BUY':
            return row['actual_return']  # Long: on gagne si ça monte
        elif row['prediction'] == 'SELL':
            return -row['actual_return']  # Short: on gagne si ça baisse
        else:  # HOLD
            return 0

    df_test['trade_pnl'] = df_test.apply(calculate_pnl, axis=1)

    # Calculer les métriques
    df_trades = df_test[df_test['prediction'] != 'HOLD'].copy()

    total_trades = len(df_trades)
    winning_trades = len(df_trades[df_trades['trade_pnl'] > 0])
    losing_trades = len(df_trades[df_trades['trade_pnl'] < 0])
    win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0

    total_return = df_test['trade_pnl'].sum()
    avg_return_per_trade = df_trades['trade_pnl'].mean() if len(df_trades) > 0 else 0

    # Calcul du Sharpe Ratio (simplifié, sans taux sans risque)
    returns_std = df_trades['trade_pnl'].std() if len(df_trades) > 0 else 1
    sharpe_ratio = (avg_return_per_trade / returns_std) * np.sqrt(252 * 4) if returns_std > 0 else 0  # Annualisé (4 trades/jour en M15)

    # Calcul du Max Drawdown
    df_test['cumulative_pnl'] = df_test['trade_pnl'].cumsum()
    df_test['cumulative_max'] = df_test['cumulative_pnl'].cummax()
    df_test['drawdown'] = df_test['cumulative_pnl'] - df_test['cumulative_max']
    max_drawdown = df_test['drawdown'].min()

    print("="*60)
    print("📊 RÉSULTATS DU BACKTESTING")
    print("="*60)
    print(f"\n📈 Performance globale:")
    print(f"   Total Return: {total_return:.2f}%")
    print(f"   Avg Return/Trade: {avg_return_per_trade:.4f}%")
    print(f"   Sharpe Ratio (annualisé): {sharpe_ratio:.2f}")
    print(f"   Max Drawdown: {max_drawdown:.2f}%")

    print(f"\n🎯 Statistiques des trades:")
    print(f"   Total trades: {total_trades}")
    print(f"   Trades gagnants: {winning_trades} ({win_rate:.1f}%)")
    print(f"   Trades perdants: {losing_trades}")

    print(f"\n📊 Répartition des prédictions:")
    pred_counts = df_test['prediction'].value_counts()
    for pred_label, pred_cnt in pred_counts.items():
        print(f"   {pred_label}: {pred_cnt} ({pred_cnt/len(df_test)*100:.1f}%)")
    return (df_test,)


@app.cell
def _(df_test, mo, pd):
    # Créer un résumé pour affichage
    backtest_summary = pd.DataFrame({
        'Métrique': ['Total Return (%)', 'Win Rate (%)', 'Sharpe Ratio', 'Max Drawdown (%)', 'Nombre de Trades'],
        'Valeur': [
            f"{df_test['trade_pnl'].sum():.2f}",
            f"{len(df_test[df_test['trade_pnl'] > 0]) / len(df_test[df_test['prediction'] != 'HOLD']) * 100:.1f}" if len(df_test[df_test['prediction'] != 'HOLD']) > 0 else "N/A",
            f"{(df_test[df_test['prediction'] != 'HOLD']['trade_pnl'].mean() / df_test[df_test['prediction'] != 'HOLD']['trade_pnl'].std()) * (252 * 4)**0.5:.2f}" if df_test[df_test['prediction'] != 'HOLD']['trade_pnl'].std() > 0 else "N/A",
            f"{df_test['drawdown'].min():.2f}",
            f"{len(df_test[df_test['prediction'] != 'HOLD'])}"
        ]
    })

    mo.ui.table(backtest_summary)
    return


@app.cell
def _(mo):
    # Courbe de P&L cumulé
    mo.md("""
    ### 📉 Courbe de P&L Cumulé
    """)
    return


@app.cell
def _(df_test):
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(12, 5))

    # P&L cumulé
    ax.plot(df_test['cumulative_pnl'].values, label='P&L Cumulé', color='blue', linewidth=1.5)
    ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)

    # Zones de drawdown
    ax.fill_between(range(len(df_test)), df_test['cumulative_pnl'].values, df_test['cumulative_max'].values,
                    alpha=0.3, color='red', label='Drawdown')

    ax.set_xlabel('Période')
    ax.set_ylabel('P&L Cumulé (%)')
    ax.set_title('Évolution du P&L Cumulé sur la période de test')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.gca()
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ## 📝 Conclusion & Prochaines Étapes

    ### Résumé du pipeline
    1. ✅ **Données chargées** depuis PostgreSQL (MT5 + Yahoo + Macro)
    2. ✅ **Features créées** (MA, RSI, Bollinger, momentum, etc.)
    3. ✅ **Labels définis** (BUY/SELL/HOLD basé sur le rendement futur)
    4. ✅ **Modèles comparés** (9 algorithmes testés)
    5. ✅ **Meilleur modèle identifié**

    ### Prochaines étapes
    1. **Sauvegarder le modèle** avec `joblib.dump()` pour réutilisation
    2. **Optimiser les hyperparamètres** (GridSearch/RandomSearch sur le meilleur modèle)
    3. **Backtesting** : Simuler les trades sur données historiques pour calculer le P&L
    4. **Intégration** : Déployer le modèle dans le pipeline Airflow pour prédictions en temps réel

    ### ⚠️ Avertissements
    - Les performances passées ne garantissent pas les performances futures
    - Le modèle doit être ré-entraîné régulièrement (drift des données)
    - Toujours utiliser un **stop-loss** en trading réel
    """)
    return


if __name__ == "__main__":
    app.run()
