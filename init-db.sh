#!/bin/bash
set -e

# Définir les variables directement
AIRFLOW_DB_NAME="airflow"
AIRFLOW_DB_USER="airflow"
AIRFLOW_DB_PASSWORD="airflow"
MLFLOW_DB_NAME="mlflow"
MLFLOW_DB_USER="mlflow"
MLFLOW_DB_PASSWORD="mlflow"

# Créer les bases de données
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Créer les bases de données si elles n'existent pas
    SELECT 'CREATE DATABASE $AIRFLOW_DB_NAME' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$AIRFLOW_DB_NAME')\gexec
    SELECT 'CREATE DATABASE $MLFLOW_DB_NAME' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$MLFLOW_DB_NAME')\gexec
    
    -- Créer les utilisateurs
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_user WHERE usename = '$AIRFLOW_DB_USER') THEN
            CREATE USER $AIRFLOW_DB_USER WITH PASSWORD '$AIRFLOW_DB_PASSWORD';
        END IF;
        IF NOT EXISTS (SELECT FROM pg_user WHERE usename = '$MLFLOW_DB_USER') THEN
            CREATE USER $MLFLOW_DB_USER WITH PASSWORD '$MLFLOW_DB_PASSWORD';
        END IF;
    END
    \$\$;
    
    -- Accorder tous les privilèges sur les bases de données
    GRANT ALL PRIVILEGES ON DATABASE $AIRFLOW_DB_NAME TO $AIRFLOW_DB_USER;
    GRANT ALL PRIVILEGES ON DATABASE $MLFLOW_DB_NAME TO $MLFLOW_DB_USER;
EOSQL

# Connexion à la base Airflow pour accorder les permissions sur le schéma public
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$AIRFLOW_DB_NAME" <<-EOSQL
    GRANT ALL ON SCHEMA public TO $AIRFLOW_DB_USER;
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $AIRFLOW_DB_USER;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $AIRFLOW_DB_USER;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $AIRFLOW_DB_USER;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $AIRFLOW_DB_USER;
EOSQL

# Connexion à la base MLflow pour accorder les permissions sur le schéma public
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$MLFLOW_DB_NAME" <<-EOSQL
    GRANT ALL ON SCHEMA public TO $MLFLOW_DB_USER;
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $MLFLOW_DB_USER;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $MLFLOW_DB_USER;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO $MLFLOW_DB_USER;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO $MLFLOW_DB_USER;
EOSQL

echo "Databases and users created successfully with proper permissions!"