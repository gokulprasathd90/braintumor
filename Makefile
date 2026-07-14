# ─── Makefile — Brain Tumour Detection ────────────────────────────────────────
#
# Targets are grouped by concern:
#   setup   — first-time developer onboarding
#   dev     — run services locally (without Docker)
#   test    — run all test suites
#   build   — production builds
#   docker  — container lifecycle
#   clean   — remove generated artefacts
#
# Usage:
#   make setup          # one-time environment bootstrap
#   make dev            # start all three services in separate terminals (tmux)
#   make test           # run every test suite
#   make docker-up      # build and start all containers
#   make clean          # remove logs, builds, and __pycache__
#
# Prerequisites: Python 3.12+, Node 20+, npm, Docker, Docker Compose v2

.DEFAULT_GOAL := help
SHELL         := bash

# ── Colour codes ──────────────────────────────────────────────────────────────
CYAN   := \033[0;36m
GREEN  := \033[0;32m
YELLOW := \033[1;33m
RED    := \033[0;31m
NC     := \033[0m   # No Colour

# ── Directory shortcuts ───────────────────────────────────────────────────────
AI   := ai-service
BE   := backend
FE   := frontend
DOCK := docker

# ── Compose file ─────────────────────────────────────────────────────────────
COMPOSE := docker compose -f $(DOCK)/docker-compose.yml

# ─────────────────────────────────────────────────────────────────────────────
# HELP
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: help
help:  ## Show this help message
	@echo ""
	@echo -e "$(CYAN)Brain Tumour Detection — available targets$(NC)"
	@echo "─────────────────────────────────────────────────────"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-22s$(NC) %s\n", $$1, $$2}'
	@echo ""

# ─────────────────────────────────────────────────────────────────────────────
# SETUP — first-time onboarding
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: setup setup-ai setup-backend setup-frontend

setup: setup-ai setup-backend setup-frontend  ## Bootstrap all three environments
	@echo -e "$(GREEN)✓ All environments ready. Run 'make dev' to start.$(NC)"

setup-ai:  ## Create Python venv and install AI service dependencies
	@echo -e "$(CYAN)→ Setting up AI service...$(NC)"
	@cd $(AI) && bash setup_env.sh

setup-backend:  ## Install Node backend dependencies and copy .env
	@echo -e "$(CYAN)→ Setting up backend...$(NC)"
	@cd $(BE) && npm ci
	@if [ ! -f $(BE)/.env ]; then \
		cp $(BE)/.env.example $(BE)/.env; \
		echo -e "  $(GREEN)✓$(NC) Created backend/.env from .env.example"; \
	else \
		echo -e "  $(YELLOW)⚠$(NC)  backend/.env already exists — skipping"; \
	fi

setup-frontend:  ## Install Node frontend dependencies and copy .env
	@echo -e "$(CYAN)→ Setting up frontend...$(NC)"
	@cd $(FE) && npm ci
	@if [ ! -f $(FE)/.env.local ]; then \
		cp $(FE)/.env.example $(FE)/.env.local; \
		echo -e "  $(GREEN)✓$(NC) Created frontend/.env.local from .env.example"; \
	else \
		echo -e "  $(YELLOW)⚠$(NC)  frontend/.env.local already exists — skipping"; \
	fi

# ─────────────────────────────────────────────────────────────────────────────
# DEV — run locally without Docker
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: dev dev-ai dev-backend dev-frontend

dev:  ## Start all services (requires tmux)
	@command -v tmux >/dev/null 2>&1 || { \
		echo -e "$(YELLOW)tmux not found — start services in separate terminals:$(NC)"; \
		echo "  make dev-ai"; \
		echo "  make dev-backend"; \
		echo "  make dev-frontend"; \
		exit 0; \
	}
	@tmux new-session -d -s brain-tumor -n ai \
		"cd $(AI) && source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload; read"
	@tmux new-window -t brain-tumor -n backend \
		"cd $(BE) && npm run dev; read"
	@tmux new-window -t brain-tumor -n frontend \
		"cd $(FE) && npm run dev; read"
	@tmux attach -t brain-tumor
	@echo -e "$(GREEN)✓ All services started in tmux session 'brain-tumor'$(NC)"

dev-ai:  ## Start AI service with hot-reload (port 8000)
	@echo -e "$(CYAN)→ Starting AI service on :8000$(NC)"
	@cd $(AI) && source .venv/bin/activate \
		&& uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

dev-backend:  ## Start backend with nodemon (port 5000)
	@echo -e "$(CYAN)→ Starting backend on :5000$(NC)"
	@cd $(BE) && npm run dev

dev-frontend:  ## Start Vite dev server with HMR (port 3000)
	@echo -e "$(CYAN)→ Starting frontend on :3000$(NC)"
	@cd $(FE) && npm run dev

# ─────────────────────────────────────────────────────────────────────────────
# TEST
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: test test-ai test-backend

test: test-ai test-backend  ## Run all test suites
	@echo -e "$(GREEN)✓ All tests complete$(NC)"

test-ai:  ## Run Python pytest suite (ai-service/tests/)
	@echo -e "$(CYAN)→ Running AI service tests...$(NC)"
	@cd $(AI) && source .venv/bin/activate && pytest -v --tb=short

test-backend:  ## Run Jest suite (backend/tests/)
	@echo -e "$(CYAN)→ Running backend tests...$(NC)"
	@cd $(BE) && npm test -- --runInBand

test-ai-coverage:  ## Run AI tests with coverage report
	@cd $(AI) && source .venv/bin/activate \
		&& pytest --cov=app --cov-report=term-missing --cov-report=html:htmlcov -v

# ─────────────────────────────────────────────────────────────────────────────
# BUILD — production artefacts
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: build build-frontend

build: build-frontend  ## Build all production artefacts
	@echo -e "$(GREEN)✓ Production build complete$(NC)"

build-frontend:  ## Compile React app to frontend/dist/
	@echo -e "$(CYAN)→ Building frontend...$(NC)"
	@cd $(FE) && npm run build
	@echo -e "$(GREEN)✓ Frontend built → frontend/dist/$(NC)"

# ─────────────────────────────────────────────────────────────────────────────
# DOCKER
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: docker-build docker-up docker-down docker-restart \
        docker-logs docker-ps docker-prune

docker-build:  ## Build all Docker images (no cache)
	@echo -e "$(CYAN)→ Building Docker images...$(NC)"
	@$(COMPOSE) build --no-cache

docker-up:  ## Build and start all containers in the background
	@echo -e "$(CYAN)→ Starting containers...$(NC)"
	@$(COMPOSE) up --build -d
	@echo -e "$(GREEN)✓ Containers running:$(NC)"
	@echo "    Frontend  → http://localhost:3000"
	@echo "    Backend   → http://localhost:5000"
	@echo "    AI Service→ http://localhost:8000"
	@echo "    API Docs  → http://localhost:8000/docs"

docker-up-dev:  ## Start containers with bind-mounted source (faster iteration)
	@$(COMPOSE) -f $(DOCK)/docker-compose.yml \
	            -f $(DOCK)/docker-compose.dev.yml up --build -d

docker-down:  ## Stop and remove containers (keeps volumes)
	@echo -e "$(CYAN)→ Stopping containers...$(NC)"
	@$(COMPOSE) down
	@echo -e "$(GREEN)✓ Containers stopped$(NC)"

docker-restart:  ## Restart all containers
	@$(COMPOSE) restart

docker-logs:  ## Tail logs from all containers
	@$(COMPOSE) logs -f

docker-logs-ai:  ## Tail logs from the AI service only
	@$(COMPOSE) logs -f ai-service

docker-logs-backend:  ## Tail logs from the backend only
	@$(COMPOSE) logs -f backend

docker-ps:  ## Show container status
	@$(COMPOSE) ps

docker-prune:  ## Remove stopped containers, dangling images, and unused volumes
	@echo -e "$(YELLOW)→ Pruning Docker resources...$(NC)"
	@docker system prune -f
	@docker volume prune -f
	@echo -e "$(GREEN)✓ Docker pruned$(NC)"

# ─────────────────────────────────────────────────────────────────────────────
# CLEAN
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: clean clean-ai clean-frontend clean-all

clean: clean-ai clean-frontend  ## Remove build artefacts and logs
	@echo -e "$(GREEN)✓ Clean complete$(NC)"

clean-ai:  ## Remove Python __pycache__, .pytest_cache, logs, htmlcov
	@echo -e "$(CYAN)→ Cleaning AI service...$(NC)"
	@find $(AI) -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find $(AI) -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@find $(AI) -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	@find $(AI) -name "*.pyc" -delete 2>/dev/null || true
	@rm -rf $(AI)/logs/*.log 2>/dev/null || true

clean-frontend:  ## Remove frontend/dist and node_modules/.cache
	@echo -e "$(CYAN)→ Cleaning frontend...$(NC)"
	@rm -rf $(FE)/dist $(FE)/node_modules/.cache 2>/dev/null || true

clean-all: clean docker-prune  ## Deep clean including venv and node_modules
	@echo -e "$(YELLOW)→ Deep cleaning (removing venv and node_modules)...$(NC)"
	@rm -rf $(AI)/.venv
	@rm -rf $(BE)/node_modules
	@rm -rf $(FE)/node_modules
	@echo -e "$(GREEN)✓ Deep clean complete — re-run 'make setup' to restore$(NC)"

# ─────────────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: env-check migrate lint-ai

env-check:  ## Verify all .env files exist (warns if missing)
	@echo -e "$(CYAN)→ Checking environment files...$(NC)"
	@for f in $(AI)/.env $(BE)/.env $(FE)/.env.local; do \
		if [ -f $$f ]; then \
			echo -e "  $(GREEN)✓$(NC) $$f"; \
		else \
			echo -e "  $(RED)✗$(NC) $$f  (missing — copy from .env.example)"; \
		fi; \
	done

migrate:  ## Run SQLite database migrations (backend)
	@echo -e "$(CYAN)→ Running database migrations...$(NC)"
	@cd $(BE) && node database/migrate.js
	@echo -e "$(GREEN)✓ Migrations complete$(NC)"

lint-ai:  ## Lint Python source with ruff (install separately: pip install ruff)
	@echo -e "$(CYAN)→ Linting AI service...$(NC)"
	@cd $(AI) && source .venv/bin/activate && ruff check app/ tests/

# ─────────────────────────────────────────────────────────────────────────────
# DATASET
# ─────────────────────────────────────────────────────────────────────────────
.PHONY: dataset-validate dataset-prepare dataset-stats dataset-info

dataset-validate:  ## Validate raw dataset structure (non-destructive)
	@echo -e "$(CYAN)→ Validating dataset...$(NC)"
	@cd $(AI) && source .venv/bin/activate \
		&& python scripts/prepare_dataset.py validate \
		   --raw-dir "$${RAW_DIR:-dataset/raw}"

dataset-prepare:  ## Validate, split, and index the dataset (writes to dataset/processed/)
	@echo -e "$(CYAN)→ Preparing dataset (train/val/test split)...$(NC)"
	@cd $(AI) && source .venv/bin/activate \
		&& python scripts/prepare_dataset.py prepare \
		   --raw-dir    "$${RAW_DIR:-dataset/raw}" \
		   --output-dir "$${OUTPUT_DIR:-dataset/processed}" \
		   --train      "$${TRAIN_RATIO:-0.70}" \
		   --val        "$${VAL_RATIO:-0.15}" \
		   --test       "$${TEST_RATIO:-0.15}" \
		   --seed       "$${SEED:-42}" \
		   $$([ "$${OVERWRITE:-0}" = "1" ] && echo "--overwrite") \
		   $$([ "$${FULL_STATS:-0}" = "1" ] && echo "--full-stats")
	@echo -e "$(GREEN)✓ Dataset prepared → $(AI)/dataset/processed/$(NC)"

dataset-prepare-overwrite:  ## Re-split dataset from scratch (overwrites existing split)
	@$(MAKE) dataset-prepare OVERWRITE=1

dataset-stats:  ## Print statistics for the raw dataset directory
	@echo -e "$(CYAN)→ Computing dataset statistics...$(NC)"
	@cd $(AI) && source .venv/bin/activate \
		&& python scripts/prepare_dataset.py stats \
		   --dir "$${STATS_DIR:-dataset/raw}" \
		   $$([ "$${FULL_STATS:-0}" = "1" ] && echo "--full")

dataset-stats-full:  ## Print full statistics including pixel mean/std (reads images)
	@$(MAKE) dataset-stats STATS_DIR="$${STATS_DIR:-dataset/raw}" FULL_STATS=1

dataset-info:  ## Print saved dataset_info.json for the processed directory
	@echo -e "$(CYAN)→ Loading dataset metadata...$(NC)"
	@cd $(AI) && source .venv/bin/activate \
		&& python scripts/prepare_dataset.py info \
		   --dir "$${INFO_DIR:-dataset/processed}"
