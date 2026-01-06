from datetime import datetime, timedelta
from airflow import DAG
from airflow.sdk import task
from airflow.utils.context import Context

import os
import pandas as pd
import requests
import psycopg2
from utils.vault_helper import get_vault

from dotenv import load_dotenv

from utils.mt5_server import import_data
from utils.alpha_vantage import get_macro_context_stooq
from utils.document_helper import extract_documents

load_dotenv()

DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1447910339155988564/ybAszOuZF9HpV2djOQb_NtNSI_lgRL1swgQhmgB6jsfj9G5OMEstRP_U4rxobcfbspwJ"

# DAG CONFIG
default_args = {
    'owner': 'orion',
    'email_on_failure': True,
    'email': 'admin@oriontrader.ai',
    'retries': 2,
    'retry_delay': timedelta(minutes=3)
}

with DAG(
    dag_id="ETL_forex_EUR_USD",
    default_args=default_args,
    description="Pipeline ETL pour données Forex EURUSD",
    catchup=False,
    tags=["forex", "etl", "orion"],
):

    @task
    def extract_data_from_metatrader(**context):
        base_path = "data/mt5"
        os.makedirs(base_path, exist_ok=True)

        now = datetime.now()
        default_start = now - timedelta(days=30)
        default_end = now

        start = context.get("data_interval_start")
        end = context.get("data_interval_end")

        if start is None or end is None or start == end:
            start = default_start
            end = default_end
            print(f"[DAG] Utilisation des dates par défaut (contexte non disponible ou DAG manuel)")
            print(f"[DAG] Période: {start} -> {end}")
        else:
            print(f"[DAG] Utilisation des dates du contexte Airflow")
            print(f"[DAG] Période: {start} -> {end}")

        df = pd.DataFrame.from_dict(
            import_data(start=start, end=end)
        )

        path = f"{base_path}/eurusd_mt5.parquet"
        df.to_parquet(path)

        return path

    @task
    def extract_data_from_api():
        base_path = "data/api"
        os.makedirs(base_path, exist_ok=True)

        print("[DAG] Récupération du contexte macro via Stooq...")
        macro_context = get_macro_context_stooq(days=365)

        paths = {}
        asset_mapping = {
            'eurusd': 'EUR/USD',
            'gbpusd': 'GBP/USD',
            'usdjpy': 'USD/JPY',
            'dxy': 'DXY (Dollar Index)',
            'spx': 'S&P 500',
            'vix': 'VIX',
            'dji': 'Dow Jones',
            'gold': 'Or (Gold)',
            'silver': 'Argent (Silver)'
        }

        for key, name in asset_mapping.items():
            if key in macro_context:
                print(f"[DAG] Sauvegarde {name}...")
                file_path = f"{base_path}/{key}_daily.parquet"
                macro_context[key].to_parquet(file_path)
                paths[key] = file_path
            else:
                print(f"[DAG] ⚠ {name} non disponible, ignoré")

        print(f"[DAG] ✓ {len(paths)} actifs macro sauvegardés")

        return paths

    @task
    def extract_data_from_document(**context):
        now = datetime.now()
        default_start = now - timedelta(days=30)
        default_end = now

        start = context.get("data_interval_start")
        end = context.get("data_interval_end")

        if start is None or end is None or start == end:
            start = default_start
            end = default_end
            print(f"[DAG] Documents - Utilisation des dates par défaut")
            print(f"[DAG] Documents - Période: {start} -> {end}")
        else:
            print(f"[DAG] Documents - Utilisation des dates du contexte Airflow")
            print(f"[DAG] Documents - Période: {start} -> {end}")

        paths = extract_documents()
        return paths

    @task
    def transform_data(mt5_path: str, api_paths: dict, doc_paths: dict):
        """
        Pipeline de transformation multi-horizon :
        - MT5 (M15) : Microstructure du marché (price action, volatilité)
        - Stooq (daily) : Régime de marché (DXY, indices, risk-on/off)
        - Eurostat : Fondamentaux macro (PIB, inflation)
        """
        base_path = "data/processed"
        os.makedirs(base_path, exist_ok=True)

        print("[TRANSFORM] ==================== DÉBUT TRANSFORMATION ====================")

        # ===== 1. CHARGEMENT MT5 (SOURCE PRINCIPALE M15) =====
        print("[TRANSFORM] 📊 Chargement données MT5 (M15)...")
        df_mt5 = pd.read_parquet(mt5_path)

        if 'time' not in df_mt5.columns:
            df_mt5 = df_mt5.reset_index()

        df_mt5['time'] = pd.to_datetime(df_mt5['time'], utc=True)
        df_mt5 = df_mt5.set_index('time').sort_index()

        print(f"[TRANSFORM] ✓ MT5 chargé: {len(df_mt5)} lignes, période {df_mt5.index.min()} → {df_mt5.index.max()}")

        # ===== 2. MERGE STOOQ (RÉGIME DE MARCHÉ DAILY) =====
        print("[TRANSFORM] 🌍 Merge données Stooq (régime de marché)...")

        asset_names = {
            'eurusd': 'eurusd_daily',
            'gbpusd': 'gbpusd_daily',
            'usdjpy': 'usdjpy_daily',
            'dxy': 'dxy',
            'spx': 'spx',
            'vix': 'vix',
            'dji': 'dji',
            'gold': 'gold',
            'silver': 'silver'
        }

        merged_count = 0
        for key, display_name in asset_names.items():
            if key in api_paths:
                try:
                    df_macro = pd.read_parquet(api_paths[key])
                    df_macro.index = pd.to_datetime(df_macro.index, utc=True)

                    # Resample daily → M15 via forward-fill
                    df_resampled = df_macro.resample('15min').ffill()
                    df_resampled.columns = [f"{display_name}_{col}" for col in df_resampled.columns]

                    # Merge
                    df_mt5 = df_mt5.merge(df_resampled, left_index=True, right_index=True, how='left')
                    merged_count += 1
                    print(f"[TRANSFORM]   ✓ {display_name} mergé ({len(df_resampled.columns)} colonnes)")
                except Exception as e:
                    print(f"[TRANSFORM]   ⚠ Erreur {display_name}: {e}")

        print(f"[TRANSFORM] ✓ {merged_count} actifs macro mergés")

        # ===== 3. MERGE EUROSTAT (FONDAMENTAUX MACRO) =====
        print("[TRANSFORM] 📈 Merge documents Eurostat (fondamentaux)...")

        try:
            df_pib = pd.read_parquet(doc_paths["pib"])
            df_pib.index = pd.to_datetime(df_pib.index, utc=True)
            df_pib_resampled = df_pib.resample('15min').ffill()
            df_mt5 = df_mt5.merge(df_pib_resampled, left_index=True, right_index=True, how='left')
            print(f"[TRANSFORM]   ✓ PIB mergé (zone euro)")
        except Exception as e:
            print(f"[TRANSFORM]   ⚠ Erreur PIB: {e}")

        try:
            df_cpi = pd.read_parquet(doc_paths["cpi"])
            df_cpi.index = pd.to_datetime(df_cpi.index, utc=True)
            df_cpi_resampled = df_cpi.resample('15min').ffill()
            df_mt5 = df_mt5.merge(df_cpi_resampled, left_index=True, right_index=True, how='left')
            print(f"[TRANSFORM]   ✓ CPI mergé (inflation)")
        except Exception as e:
            print(f"[TRANSFORM]   ⚠ Erreur CPI: {e}")

        try:
            df_events = pd.read_parquet(doc_paths["events"])
            df_events['time'] = pd.to_datetime(df_events['time'], utc=True)
            df_events = df_events.set_index('time').sort_index()

            # Dernier événement connu (forward-fill)
            df_mt5["event_title"] = df_events["title"].reindex(df_mt5.index, method="ffill")
            df_mt5["event_impact"] = df_events["impact"].reindex(df_mt5.index, method="ffill")
            print(f"[TRANSFORM]   ✓ Événements économiques mergés")
        except Exception as e:
            print(f"[TRANSFORM]   ⚠ Erreur événements: {e}")

        # ===== 4. FEATURE ENGINEERING MULTI-HORIZON =====
        print("[TRANSFORM] 🔧 Feature Engineering multi-horizon...")

        # --- HORIZON COURT (Minutes) : MT5 Price Action ---
        print("[TRANSFORM]   📊 Features MT5 (microstructure)...")
        df_mt5["close_diff"] = df_mt5["close"].diff()
        df_mt5["close_return"] = df_mt5["close"].pct_change()
        df_mt5["high_low_range"] = df_mt5["high"] - df_mt5["low"]
        df_mt5["volatility_1h"] = df_mt5["close"].rolling(window=4).std()
        df_mt5["volatility_4h"] = df_mt5["close"].rolling(window=16).std()

        # Momentum court terme
        df_mt5["momentum_15m"] = df_mt5["close"] - df_mt5["close"].shift(1)
        df_mt5["momentum_1h"] = df_mt5["close"] - df_mt5["close"].shift(4)
        df_mt5["momentum_4h"] = df_mt5["close"] - df_mt5["close"].shift(16)

        # Patterns de bougies
        df_mt5["body"] = df_mt5["close"] - df_mt5["open"]
        df_mt5["upper_shadow"] = df_mt5["high"] - df_mt5[["open", "close"]].max(axis=1)
        df_mt5["lower_shadow"] = df_mt5[["open", "close"]].min(axis=1) - df_mt5["low"]

        print(f"[TRANSFORM]     ✓ 11 features MT5 créées")

        # --- HORIZON MOYEN (Heures/Jours) : Régime de marché Stooq ---
        print("[TRANSFORM]   🌍 Features Stooq (régime de marché)...")
        features_stooq = 0

        if 'dxy_close' in df_mt5.columns:
            df_mt5["dxy_trend_1h"] = df_mt5["dxy_close"].pct_change(periods=4)
            df_mt5["dxy_trend_4h"] = df_mt5["dxy_close"].pct_change(periods=16)
            df_mt5["dxy_strength"] = (df_mt5["dxy_close"] - df_mt5["dxy_close"].rolling(96).mean()) / df_mt5["dxy_close"].rolling(96).std()
            features_stooq += 3

        if 'vix_close' in df_mt5.columns:
            df_mt5["vix_level"] = df_mt5["vix_close"]
            df_mt5["vix_change"] = df_mt5["vix_close"].pct_change(periods=4)
            df_mt5["market_stress"] = (df_mt5["vix_close"] > 20).astype(int)
            features_stooq += 3

        if 'spx_close' in df_mt5.columns:
            df_mt5["spx_trend"] = df_mt5["spx_close"].pct_change(periods=4)
            df_mt5["risk_on"] = (df_mt5["spx_trend"] > 0).astype(int)
            features_stooq += 2

        if 'gold_close' in df_mt5.columns:
            df_mt5["gold_trend"] = df_mt5["gold_close"].pct_change(periods=4)
            df_mt5["safe_haven"] = (df_mt5["gold_trend"] > 0).astype(int)
            features_stooq += 2

        print(f"[TRANSFORM]     ✓ {features_stooq} features Stooq créées")

        # --- HORIZON LONG (Semaines/Mois) : Fondamentaux Eurostat ---
        print("[TRANSFORM]   📈 Features Eurostat (fondamentaux)...")
        features_eurostat = 0

        if 'eurozone_pib' in df_mt5.columns:
            df_mt5["pib_change"] = df_mt5["eurozone_pib"].pct_change().fillna(0)
            df_mt5["pib_growth"] = (df_mt5["pib_change"] > 0).astype(int)
            features_eurostat += 2

        if 'eurozone_cpi' in df_mt5.columns:
            df_mt5["cpi_change"] = df_mt5["eurozone_cpi"].pct_change().fillna(0)
            df_mt5["inflation_pressure"] = (df_mt5["cpi_change"] > 0.02).astype(int)
            features_eurostat += 2

        # Event impact encoding
        if 'event_impact' in df_mt5.columns:
            impact_map = {"High": 3, "Medium": 2, "Low": 1}
            df_mt5["event_impact_score"] = df_mt5["event_impact"].map(impact_map).fillna(0)
            features_eurostat += 1

        print(f"[TRANSFORM]     ✓ {features_eurostat} features Eurostat créées")

        # --- FEATURES COMPOSITES (MULTI-HORIZON) ---
        print("[TRANSFORM]   🎯 Features composites (multi-horizon)...")

        # Alignement macro/micro
        if 'dxy_trend_1h' in df_mt5.columns and 'close_return' in df_mt5.columns:
            df_mt5["macro_micro_aligned"] = (
                (df_mt5["close_return"] > 0) & (df_mt5["dxy_trend_1h"] < 0)
            ).astype(int)

        # Biais directionnel (fondamentaux + régime)
        if 'pib_growth' in df_mt5.columns and 'risk_on' in df_mt5.columns:
            df_mt5["euro_strength_bias"] = df_mt5["pib_growth"] * df_mt5["risk_on"]

        print(f"[TRANSFORM]     ✓ Features composites créées")

        # ===== 5. NETTOYAGE ET SAUVEGARDE =====
        print("[TRANSFORM] 🧹 Nettoyage et sauvegarde...")

        initial_rows = len(df_mt5)
        df_mt5 = df_mt5.dropna(subset=['close', 'open', 'high', 'low'])

        # Limiter les NaN sur les features
        df_mt5 = df_mt5.ffill().fillna(0)

        final_rows = len(df_mt5)
        print(f"[TRANSFORM]   ℹ {initial_rows - final_rows} lignes supprimées (NaN)")

        # Sauvegarde
        out_path = os.path.join(base_path, "eurusd_features.parquet")
        df_mt5.to_parquet(out_path)

        print(f"[TRANSFORM] ==================== FIN TRANSFORMATION ====================")
        print(f"[TRANSFORM] ✅ Dataset final: {df_mt5.shape[0]} lignes × {df_mt5.shape[1]} colonnes")
        print(f"[TRANSFORM] ✅ Fichier sauvegardé: {out_path}")

        return {
            "path": out_path,
            "rows": df_mt5.shape[0],
            "columns": df_mt5.shape[1],
            "date_range": f"{df_mt5.index.min()} → {df_mt5.index.max()}"
        }

    @task
    def load_to_db(data: dict):
        """
        Charge les données transformées dans PostgreSQL.
        Table: forex_features
        """
        print("[LOAD] ==================== DÉBUT CHARGEMENT ====================")

        vault = get_vault()
        db_config = {
            'host': 'postgres',
            'port': 5432,
            'database': vault.get_secret('Database', 'POSTGRES_DB'),
            'user': vault.get_secret('Database', 'POSTGRES_USER'),
            'password': vault.get_secret('Database', 'POSTGRES_PASSWORD')
        }

        try:
            # Connexion PostgreSQL
            print("[LOAD] 🔌 Connexion à PostgreSQL...")
            conn = psycopg2.connect(**db_config)
            cursor = conn.cursor()

            # Création de la table si elle n'existe pas
            print("[LOAD] 📋 Création/vérification de la table...")
            create_table_query = """
            CREATE TABLE IF NOT EXISTS forex_features (
                time TIMESTAMP WITH TIME ZONE PRIMARY KEY,
                symbol VARCHAR(10) DEFAULT 'EURUSD',

                -- MT5 Raw Data
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                tick_volume REAL,

                -- MT5 Features (microstructure)
                close_diff REAL,
                close_return REAL,
                high_low_range REAL,
                volatility_1h REAL,
                volatility_4h REAL,
                momentum_15m REAL,
                momentum_1h REAL,
                momentum_4h REAL,
                body REAL,
                upper_shadow REAL,
                lower_shadow REAL,

                -- Stooq Features (régime de marché)
                dxy_close REAL,
                dxy_trend_1h REAL,
                dxy_trend_4h REAL,
                dxy_strength REAL,
                vix_close REAL,
                vix_level REAL,
                vix_change REAL,
                market_stress INTEGER,
                spx_close REAL,
                spx_trend REAL,
                risk_on INTEGER,
                gold_close REAL,
                gold_trend REAL,
                safe_haven INTEGER,

                -- Eurostat Features (fondamentaux)
                eurozone_pib REAL,
                pib_change REAL,
                pib_growth INTEGER,
                eurozone_cpi REAL,
                cpi_change REAL,
                inflation_pressure INTEGER,
                event_title TEXT,
                event_impact VARCHAR(10),
                event_impact_score INTEGER,

                -- Features Composites
                macro_micro_aligned INTEGER,
                euro_strength_bias INTEGER,

                -- Metadata
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                pipeline_run_id VARCHAR(100)
            );

            CREATE INDEX IF NOT EXISTS idx_forex_features_time ON forex_features(time);
            CREATE INDEX IF NOT EXISTS idx_forex_features_symbol ON forex_features(symbol);
            """
            cursor.execute(create_table_query)
            conn.commit()
            print("[LOAD] ✓ Table 'forex_features' prête")

            # Chargement des données
            print(f"[LOAD] 📦 Chargement des données depuis {data['path']}...")
            df = pd.read_parquet(data['path'])

            # Préparation pour l'insertion
            df = df.reset_index()
            pipeline_run_id = datetime.now().isoformat()

            # Insertion par batch (plus efficace)
            print(f"[LOAD] ⬆ Insertion de {len(df)} lignes...")

            # Préparer les colonnes (seulement celles qui existent)
            columns = [col for col in df.columns if col in [
                'time', 'open', 'high', 'low', 'close', 'tick_volume',
                'close_diff', 'close_return', 'high_low_range', 'volatility_1h', 'volatility_4h',
                'momentum_15m', 'momentum_1h', 'momentum_4h', 'body', 'upper_shadow', 'lower_shadow',
                'dxy_close', 'dxy_trend_1h', 'dxy_trend_4h', 'dxy_strength',
                'vix_close', 'vix_level', 'vix_change', 'market_stress',
                'spx_close', 'spx_trend', 'risk_on',
                'gold_close', 'gold_trend', 'safe_haven',
                'eurozone_pib', 'pib_change', 'pib_growth',
                'eurozone_cpi', 'cpi_change', 'inflation_pressure',
                'event_title', 'event_impact', 'event_impact_score',
                'macro_micro_aligned', 'euro_strength_bias'
            ]]

            # Insertion avec ON CONFLICT (update si déjà existant)
            inserted = 0
            updated = 0

            for _, row in df.iterrows():
                values = [row[col] if col in row else None for col in columns]
                values.append(pipeline_run_id)

                placeholders = ','.join(['%s'] * (len(columns) + 1))
                insert_query = f"""
                INSERT INTO forex_features ({','.join(columns)}, pipeline_run_id)
                VALUES ({placeholders})
                ON CONFLICT (time) DO UPDATE SET
                    {','.join([f'{col}=EXCLUDED.{col}' for col in columns if col != 'time'])},
                    pipeline_run_id=EXCLUDED.pipeline_run_id
                """

                cursor.execute(insert_query, values)

                if cursor.rowcount > 0:
                    if cursor.statusmessage.startswith('INSERT'):
                        inserted += 1
                    else:
                        updated += 1

            conn.commit()

            print(f"[LOAD] ✅ {inserted} lignes insérées, {updated} lignes mises à jour")

            # Statistiques
            cursor.execute("SELECT COUNT(*), MIN(time), MAX(time) FROM forex_features")
            total, min_time, max_time = cursor.fetchone()

            print(f"[LOAD] 📊 Table finale: {total} lignes totales ({min_time} → {max_time})")

            cursor.close()
            conn.close()

            print("[LOAD] ==================== FIN CHARGEMENT ====================")

            return {
                "status": "success",
                "inserted": inserted,
                "updated": updated,
                "total_rows": total,
                "date_range": f"{min_time} → {max_time}",
                "pipeline_run_id": pipeline_run_id
            }

        except Exception as e:
            print(f"[LOAD] ❌ Erreur chargement: {e}")
            raise

    @task
    def validate(load_result: dict):
        """
        Valide la qualité et cohérence des données chargées.
        Vérifie:
        - Nombre de lignes suffisant
        - Pas de colonnes entièrement NULL
        - Cohérence temporelle
        - Valeurs aberrantes
        """
        print("[VALIDATE] ==================== DÉBUT VALIDATION ====================")

        if load_result["status"] != "success":
            print("[VALIDATE] ❌ Chargement échoué, validation annulée")
            return {"status": "failed", "reason": "Load failed"}

        vault = get_vault()
        db_config = {
            'host': 'postgres',
            'port': 5432,
            'database': vault.get_secret('Database', 'POSTGRES_DB'),
            'user': vault.get_secret('Database', 'POSTGRES_USER'),
            'password': vault.get_secret('Database', 'POSTGRES_PASSWORD')
        }

        try:
            conn = psycopg2.connect(**db_config)
            cursor = conn.cursor()

            validation_results = {}
            errors = []
            warnings = []

            # 1. Vérifier le nombre de lignes
            print("[VALIDATE] 🔢 Vérification du nombre de lignes...")
            cursor.execute("SELECT COUNT(*) FROM forex_features WHERE pipeline_run_id = %s", (load_result["pipeline_run_id"],))
            row_count = cursor.fetchone()[0]

            if row_count < 100:
                errors.append(f"Trop peu de données: {row_count} lignes (minimum: 100)")
            else:
                validation_results["row_count"] = f"✓ {row_count} lignes"

            # 2. Vérifier les colonnes critiques (ne doivent pas être NULL)
            print("[VALIDATE] 🔍 Vérification des colonnes critiques...")
            critical_columns = ['open', 'high', 'low', 'close']

            for col in critical_columns:
                cursor.execute(f"SELECT COUNT(*) FROM forex_features WHERE pipeline_run_id = %s AND {col} IS NULL", (load_result["pipeline_run_id"],))
                null_count = cursor.fetchone()[0]

                if null_count > 0:
                    errors.append(f"Colonne {col}: {null_count} valeurs NULL")
                else:
                    validation_results[f"{col}_nulls"] = "✓ Aucune valeur NULL"

            # 3. Vérifier la cohérence des prix (high >= low)
            print("[VALIDATE] 📊 Vérification cohérence des prix...")
            cursor.execute("""
                SELECT COUNT(*) FROM forex_features
                WHERE pipeline_run_id = %s AND (high < low OR high < open OR high < close OR low > open OR low > close)
            """, (load_result["pipeline_run_id"],))
            invalid_prices = cursor.fetchone()[0]

            if invalid_prices > 0:
                errors.append(f"Prix incohérents: {invalid_prices} lignes")
            else:
                validation_results["price_coherence"] = "✓ Prix cohérents"

            # 4. Vérifier les valeurs aberrantes
            print("[VALIDATE] ⚠ Détection valeurs aberrantes...")
            cursor.execute("""
                SELECT
                    AVG(close) as avg_close,
                    STDDEV(close) as std_close,
                    MIN(close) as min_close,
                    MAX(close) as max_close
                FROM forex_features WHERE pipeline_run_id = %s
            """, (load_result["pipeline_run_id"],))

            avg, std, min_val, max_val = cursor.fetchone()

            if std and avg:
                # Valeurs à plus de 5 sigma
                cursor.execute("""
                    SELECT COUNT(*) FROM forex_features
                    WHERE pipeline_run_id = %s AND (close > %s OR close < %s)
                """, (load_result["pipeline_run_id"], avg + 5 * std, avg - 5 * std))

                outliers = cursor.fetchone()[0]

                if outliers > row_count * 0.01:  # Plus de 1% d'outliers
                    warnings.append(f"Valeurs aberrantes: {outliers} lignes ({outliers/row_count*100:.1f}%)")
                else:
                    validation_results["outliers"] = f"✓ {outliers} outliers (<1%)"

            # 5. Vérifier la continuité temporelle
            print("[VALIDATE] 🕐 Vérification continuité temporelle...")
            cursor.execute("""
                WITH time_gaps AS (
                    SELECT
                        time,
                        LAG(time) OVER (ORDER BY time) as prev_time,
                        time - LAG(time) OVER (ORDER BY time) as gap
                    FROM forex_features WHERE pipeline_run_id = %s
                )
                SELECT COUNT(*) FROM time_gaps WHERE gap > INTERVAL '1 hour'
            """, (load_result["pipeline_run_id"],))

            gaps = cursor.fetchone()[0]

            if gaps > row_count * 0.1:  # Plus de 10% de gaps
                warnings.append(f"Gaps temporels importants: {gaps} gaps")
            else:
                validation_results["time_continuity"] = f"✓ {gaps} gaps (<10%)"

            # 6. Vérifier la présence de features
            print("[VALIDATE] 🔧 Vérification présence des features...")
            feature_columns = ['close_return', 'volatility_1h', 'dxy_trend_1h', 'vix_level', 'pib_change']

            present_features = 0
            for col in feature_columns:
                cursor.execute(f"""
                    SELECT COUNT(*) FROM information_schema.columns
                    WHERE table_name='forex_features' AND column_name='{col}'
                """)

                if cursor.fetchone()[0] > 0:
                    cursor.execute(f"SELECT COUNT(*) FROM forex_features WHERE pipeline_run_id = %s AND {col} IS NOT NULL", (load_result["pipeline_run_id"],))
                    non_null = cursor.fetchone()[0]

                    if non_null > row_count * 0.5:  # Au moins 50% non-NULL
                        present_features += 1

            validation_results["features"] = f"✓ {present_features}/{len(feature_columns)} features présentes"

            cursor.close()
            conn.close()

            # Résultat final
            print("[VALIDATE] ==================== RÉSULTATS ====================")

            for key, value in validation_results.items():
                print(f"[VALIDATE] {value}")

            if errors:
                print("[VALIDATE] ❌ ERREURS:")
                for error in errors:
                    print(f"[VALIDATE]   • {error}")

            if warnings:
                print("[VALIDATE] ⚠ AVERTISSEMENTS:")
                for warning in warnings:
                    print(f"[VALIDATE]   • {warning}")

            if errors:
                status = "failed"
                message = f"❌ Validation échouée: {len(errors)} erreur(s)"
            elif warnings:
                status = "success_with_warnings"
                message = f"⚠ Validation réussie avec {len(warnings)} avertissement(s)"
            else:
                status = "success"
                message = "✅ Validation complète réussie"

            print(f"[VALIDATE] {message}")
            print("[VALIDATE] ==================== FIN VALIDATION ====================")

            return {
                "status": status,
                "message": message,
                "errors": errors,
                "warnings": warnings,
                "validations": validation_results
            }

        except Exception as e:
            print(f"[VALIDATE] ❌ Erreur validation: {e}")
            return {
                "status": "error",
                "message": f"Erreur validation: {str(e)}"
            }

    @task
    def notify(validation_result: dict):
        """
        Envoie une notification Discord avec le résultat du pipeline.
        """
        status_emoji = {
            "success": "✅",
            "success_with_warnings": "⚠",
            "failed": "❌",
            "error": "🔥"
        }

        status = validation_result.get("status", "error")
        emoji = status_emoji.get(status, "❓")

        message = f"{emoji} **Pipeline ETL EURUSD terminé**\n\n"
        message += f"**Statut:** {validation_result.get('message', 'Inconnu')}\n"
        message += f"**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

        if validation_result.get("validations"):
            message += "**Validations:**\n"
            for key, value in validation_result["validations"].items():
                message += f"• {value}\n"

        if validation_result.get("warnings"):
            message += "\n**Avertissements:**\n"
            for warning in validation_result["warnings"]:
                message += f"• {warning}\n"

        if validation_result.get("errors"):
            message += "\n**Erreurs:**\n"
            for error in validation_result["errors"]:
                message += f"• {error}\n"

        try:
            response = requests.post(DISCORD_WEBHOOK, json={"content": message})
            response.raise_for_status()
            print(f"[NOTIFY] ✓ Notification Discord envoyée")
            return "Notification sent"
        except Exception as e:
            print(f"[NOTIFY] ⚠ Erreur envoi notification: {e}")
            return f"Notification failed: {e}"

    # ===========================================================
    # CHAÎNAGE DU PIPELINE
    # ===========================================================

    # Extraction
    mt5_data = extract_data_from_metatrader()
    api_data = extract_data_from_api()
    document_data = extract_data_from_document()

    # Transformation
    transformed_data = transform_data(mt5_data, api_data, document_data)

    # Chargement
    load_result = load_to_db(transformed_data)

    # Validation
    validation = validate(load_result)

    # Notification
    notify(validation)
