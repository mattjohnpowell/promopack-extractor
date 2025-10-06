# Makefile for PromoPack Extractor

.PHONY: help install install-dev test test-cov lint format security clean build run docker-build docker-run

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install production dependencies
	pip install -r requirements.txt
	pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl

install-dev: ## Install development dependencies
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl

test: ## Run tests
	pytest tests/ -v

test-cov: ## Run tests with coverage
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term

lint: ## Run linting checks
	black --check --diff .
	isort --check-only --diff .
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
	mypy . --ignore-missing-imports --no-strict-optional

format: ## Format code
	black .
	isort .

security: ## Run security checks
	bandit -r . -f txt
	safety check

clean: ## Clean up cache files and build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf dist/
	rm -rf build/

build: ## Build the application
	python -m pip install --upgrade build
	python -m build

run: ## Run the application locally (requires environment variables set)
	uvicorn main:app --reload --host 0.0.0.0 --port 8000

run-prod: ## Run the application in production mode
	uvicorn main:app --host 0.0.0.0 --port 8000

podman-build: ## Build Podman container image
	podman build -t promopack-extractor:latest .

podman-run: ## Run Podman container (requires .env file with API keys)
	podman run -d --name promopack-extractor \
		-p 8000:8000 \
		--env-file .env \
		promopack-extractor:latest

podman-run-dev: ## Run Podman container in development mode
	podman run -d --name promopack-extractor \
		-p 8000:8000 \
		-e API_KEY_SECRET=demo-key \
		-e LANGEXTRACT_API_KEY=demo-langextract-key \
		-e DATABASE_URL=sqlite:///./dev.db \
		-e ENV=dev \
		promopack-extractor:latest

podman-stop: ## Stop and remove Podman container
	podman stop promopack-extractor || true
	podman rm promopack-extractor || true

podman-logs: ## View Podman container logs
	podman logs -f promopack-extractor

podman-test: ## Run tests in Podman container
	podman run --rm promopack-extractor:latest pytest tests/ -v

health-check: ## Test the health endpoint
	curl -f http://localhost:8000/health || echo "Service not running"

api-docs: ## Open API documentation in browser
	@echo "API documentation available at: http://localhost:8000/docs"
	@echo "ReDoc documentation available at: http://localhost:8000/redoc"

docker-build: ## Build Docker image (legacy)
	docker build -t promo-pack-extractor .

docker-run: ## Run Docker container (legacy)
	docker run -p 8000:8000 promo-pack-extractor

docker-test: ## Run tests in Docker (legacy)
	docker run --rm promo-pack-extractor pytest tests/ -v

setup-dev: ## Set up development environment
	cp .env.example .env
	@echo "Please edit .env file with your API keys"
	@echo "Required: API_KEY_SECRET and LANGEXTRACT_API_KEY"

all: install-dev lint test security ## Run full development pipeline