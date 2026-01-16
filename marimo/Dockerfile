FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    marimo \
    pandas \
    numpy \
    scikit-learn \
    xgboost \
    lightgbm \
    hvac \
    psycopg[binary] \
    matplotlib \
    seaborn \
    plotly \
    mlflow

# Créer le dossier notebooks
RUN mkdir -p /app/notebooks

# Expose Marimo port
EXPOSE 2718

# Lancer Marimo en mode serveur (dashboard avec tous les notebooks)
CMD ["marimo", "edit", "--host", "0.0.0.0", "--port", "2718", "--no-token", "/app/notebooks"]
