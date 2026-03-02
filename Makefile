# Makefile pour OrionTrader
# Simplifie les commandes courantes

.PHONY: help install test lint clean docker run

# Couleurs pour les messages
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m # No Color

help: ## Affiche cette aide
	@echo "$(GREEN)OrionTrader - Commandes disponibles:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

install: ## Installe toutes les dépendances
	@echo "$(GREEN)Installing dependencies...$(NC)"
	pip install -r requirements-dev.txt
	pip install -r airflow/requirements.txt
	pip install -r fastapi/requirements.txt
	pip install -r marimo/requirements.txt
	pip install -r streamlit/requirements.txt

install-dev: ## Installe dépendances de développement uniquement
	@echo "$(GREEN)Installing dev dependencies...$(NC)"
	pip install -r requirements-dev.txt

# ============================================================================
# TESTS
# ============================================================================

test: ## Exécute tous les tests
	@echo "$(GREEN)Running all tests...$(NC)"
	pytest tests/ -v

test-unit: ## Exécute tests unitaires
	@echo "$(GREEN)Running unit tests...$(NC)"
	pytest tests/ -m unit -v

test-integration: ## Exécute tests d'intégration
	@echo "$(GREEN)Running integration tests...$(NC)"
	pytest tests/ -m integration -v

test-ml: ## Exécute tests ML
	@echo "$(GREEN)Running ML tests...$(NC)"
	pytest tests/ -m ml -v

test-api: ## Exécute tests API
	@echo "$(GREEN)Running API tests...$(NC)"
	pytest tests/ -m api -v

test-fast: ## Exécute tests rapides (sans slow)
	@echo "$(GREEN)Running fast tests...$(NC)"
	pytest tests/ -m "not slow" -v

test-parallel: ## Exécute tests en parallèle
	@echo "$(GREEN)Running tests in parallel...$(NC)"
	pytest tests/ -n auto -v

test-coverage: ## Génère rapport de couverture HTML
	@echo "$(GREEN)Generating coverage report...$(NC)"
	pytest tests/ --cov=airflow --cov=fastapi --cov-report=html --cov-report=term
	@echo "$(GREEN)Coverage report: htmlcov/index.html$(NC)"

test-watch: ## Exécute tests en mode watch
	@echo "$(GREEN)Running tests in watch mode...$(NC)"
	pytest-watch tests/ -- -v

# ============================================================================
# CODE QUALITY
# ============================================================================

lint: ## Vérifie qualité du code (black, isort, flake8)
	@echo "$(GREEN)Running linters...$(NC)"
	black --check airflow/ fastapi/ tests/
	isort --check-only airflow/ fastapi/ tests/
	flake8 airflow/ fastapi/ tests/ --max-line-length=120

format: ## Formate le code automatiquement
	@echo "$(GREEN)Formatting code...$(NC)"
	black airflow/ fastapi/ tests/
	isort airflow/ fastapi/ tests/

pylint: ## Exécute pylint
	@echo "$(GREEN)Running pylint...$(NC)"
	pylint airflow/services/ airflow/clients/ fastapi/app/ --max-line-length=120

mypy: ## Exécute mypy (type checking)
	@echo "$(GREEN)Running mypy...$(NC)"
	mypy airflow/ fastapi/

# ============================================================================
# DOCKER
# ============================================================================

docker-build: ## Build toutes les images Docker
	@echo "$(GREEN)Building Docker images...$(NC)"
	docker-compose build

docker-up: ## Démarre tous les services Docker
	@echo "$(GREEN)Starting Docker services...$(NC)"
	docker-compose up -d

docker-down: ## Arrête tous les services Docker
	@echo "$(GREEN)Stopping Docker services...$(NC)"
	docker-compose down

docker-logs: ## Affiche logs Docker
	docker-compose logs -f

docker-ps: ## Liste les containers Docker
	docker-compose ps

docker-clean: ## Nettoie images/volumes Docker
	@echo "$(GREEN)Cleaning Docker...$(NC)"
	docker-compose down -v
	docker system prune -f

# ============================================================================
# DATABASE
# ============================================================================

db-init: ## Initialise la base de données
	@echo "$(GREEN)Initializing database...$(NC)"
	docker-compose up -d postgres
	sleep 5
	docker-compose exec postgres bash /docker-entrypoint-initdb.d/init-db.sh

db-migrate: ## Exécute migrations Airflow
	@echo "$(GREEN)Running Airflow migrations...$(NC)"
	docker-compose exec airflow airflow db migrate

db-backup: ## Backup de la base de données
	@echo "$(GREEN)Backing up database...$(NC)"
	docker-compose exec postgres pg_dump -U orion trading_data > backup_$(shell date +%Y%m%d_%H%M%S).sql

# ============================================================================
# AIRFLOW
# ============================================================================

airflow-init: ## Initialise Airflow
	@echo "$(GREEN)Initializing Airflow...$(NC)"
	docker-compose exec airflow airflow db init
	docker-compose exec airflow airflow users create \
		--username admin \
		--password admin \
		--firstname Admin \
		--lastname User \
		--role Admin \
		--email admin@oriontrader.com

airflow-trigger: ## Déclenche le DAG ETL
	@echo "$(GREEN)Triggering ETL DAG...$(NC)"
	docker-compose exec airflow airflow dags trigger ETL_forex_pipeline

# ============================================================================
# MLFLOW
# ============================================================================

mlflow-ui: ## Ouvre MLflow UI
	@echo "$(GREEN)Opening MLflow UI...$(NC)"
	open http://localhost:5000

mlflow-models: ## Liste les modèles MLflow
	@echo "$(GREEN)Listing MLflow models...$(NC)"
	docker-compose exec mlflow mlflow models list

# ============================================================================
# CLEAN
# ============================================================================

clean: ## Nettoie fichiers temporaires
	@echo "$(GREEN)Cleaning temporary files...$(NC)"
	rm -rf .pytest_cache htmlcov .coverage coverage.xml junit.xml
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.log" -delete

clean-all: clean docker-clean ## Nettoie tout (fichiers + Docker)
	@echo "$(GREEN)Cleaned everything$(NC)"

# ============================================================================
# DEV
# ============================================================================

dev-setup: install docker-build db-init airflow-init ## Setup complet environnement de dev
	@echo "$(GREEN)Dev environment ready!$(NC)"
	@echo "Access:"
	@echo "  - Airflow:  http://localhost:8080"
	@echo "  - FastAPI:  http://localhost:8000/docs"
	@echo "  - MLflow:   http://localhost:5000"
	@echo "  - Grafana:  http://localhost:3000"

run-local: ## Démarre environnement de dev
	@echo "$(GREEN)Starting local environment...$(NC)"
	docker-compose up -d postgres mlflow vault prometheus grafana
	@echo "$(GREEN)Local environment ready!$(NC)"

# ============================================================================
# CI/CD
# ============================================================================

ci-test: test-fast lint ## Exécute tests CI/CD localement
	@echo "$(GREEN)CI tests passed!$(NC)"

ci-full: test lint ## Exécute tous les tests CI/CD
	@echo "$(GREEN)Full CI tests passed!$(NC)"

# ============================================================================
# DOCUMENTATION
# ============================================================================

docs: ## Génère documentation
	@echo "$(GREEN)Generating documentation...$(NC)"
	# TODO: Add sphinx/mkdocs

# ============================================================================
# DEFAULT
# ============================================================================

.DEFAULT_GOAL := help
