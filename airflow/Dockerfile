FROM python:3.12-slim

# Variables d'environnement
ENV AIRFLOW_HOME=/opt/airflow
WORKDIR $AIRFLOW_HOME

# Dépendances système requises
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    default-libmysqlclient-dev \
    libsasl2-dev \
    libssl-dev \
    libffi-dev \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Installer Airflow (dernière version)
RUN pip install --upgrade pip setuptools wheel \
    && pip install "apache-airflow[postgres]"

# Créer les dossiers nécessaires
RUN mkdir -p /opt/airflow/dags /opt/airflow/plugins /opt/airflow/config /opt/airflow/logs

# Installer rpyc pour la connexion au serveur MT5
RUN pip install --no-cache-dir rpyc

# Copier et installer les dépendances supplémentaires
COPY requirements.txt /tmp/requirements.txt
# Installer les packages en excluant MetaTrader5 et mt5linux (Windows only ou nécessite compilation)
RUN grep -v "MetaTrader5\|mt5linux" /tmp/requirements.txt > /tmp/requirements_filtered.txt && \
    pip install --no-cache-dir -r /tmp/requirements_filtered.txt

# Port Webserver
EXPOSE 8080

# Commande par défaut (sera overridée par docker-compose)
CMD ["airflow", "standalone"]