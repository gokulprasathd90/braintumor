# Brain Tumour Detection

A full-stack application for MRI brain tumour classification using deep learning.

| Service | Technology | Port |
|---|---|---|
| **Frontend** | React 18 + Vite + Tailwind CSS | 3000 |
| **Backend** | Node.js 20 + Express + SQLite | 5000 |
| **AI Service** | Python 3.12 + FastAPI + TensorFlow | 8000 |

The AI service classifies MRI scans into four categories: **glioma**, **meningioma**, **no tumour**, and **pituitary** tumour, using EfficientNetB3 (default), VGG-16, ResNet-50, or a custom CNN. Grad-CAM heatmaps provide visual explainability.

---

## Prerequisites

| Tool | Minimum version | Install |
|---|---|---|
| Python | 3.12 | [python.org](https://www.python.org/downloads/) |
| Node.js | 20 LTS | [nodejs.org](https://nodejs.org/) |
| npm | 10 | bundled with Node |
| Docker | 24 | [docs.docker.com/get-docker](https://docs.docker.com/get-docker/) |
| Docker Compose | v2 (plugin) | bundled with Docker Desktop |
| GNU Make | any | Windows: [gnuwin32](https://gnuwin32.sourceforge.net/packages/make.htm) or WSL |

---

## Quick-start (local, no Docker)

### 1. Clone and bootstrap

```bash
git clone <repo-url>
cd BRAINTUMOR
make setup          # creates .venv, npm ci for backend + frontend, copies .env files
```

On Windows without Make:

```powershell
# AI service
cd ai-service
.\setup_env.ps1

# Backend
cd ..\backend
npm ci
copy .env.example .env

# Frontend
cd ..\frontend
npm ci
copy .env.example .env.local
```

### 2. Edit environment files

Review and adjust the copied `.env` files before starting:

```
ai-service/.env        ← AI service config (model paths, ports, classes)
backend/.env           ← Backend config (port, DB path, upload dir)
frontend/.env.local    ← Frontend config (API URLs, feature flags)
```

### 3. Run database migrations

```bash
make migrate
# or: cd backend && node database/migrate.js
```

### 4. Start all services

Each service must run in its own terminal (or use `make dev` with tmux):

```bash
# Terminal 1 — AI Service
cd ai-service
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Backend
cd backend
npm run dev

# Terminal 3 — Frontend
cd frontend
npm run dev
```

**Or with tmux (Linux/macOS):**

```bash
make dev
```

### 5. Open the app

- Frontend: http://localhost:3000
- Backend API: http://localhost:5000
- AI Service API docs: http://localhost:8000/docs

---

## Quick-start (Docker)

```bash
# 1. Copy env files
cp backend/.env.example   backend/.env
cp frontend/.env.example  frontend/.env.local
cp ai-service/.env.example ai-service/.env

# 2. Build and start
make docker-up

# Equivalent without Make:
docker compose -f docker/docker-compose.yml up --build -d
```

Services will be available at the same ports (3000 / 5000 / 8000) once all health checks pass.

To follow logs:

```bash
make docker-logs            # all services
make docker-logs-ai         # AI service only
make docker-logs-backend    # backend only
```

To stop:

```bash
make docker-down
```

---

## Environment variables reference

### AI Service (`ai-service/.env`)

| Variable | Default | Description |
|---|---|---|
| `AI_SERVICE_HOST` | `0.0.0.0` | Bind address |
| `AI_SERVICE_PORT` | `8000` | Listen port |
| `AI_SERVICE_ENV` | `development` | `development` \| `production` |
| `AI_SERVICE_DEBUG` | `true` | Enable debug mode |
| `ALLOWED_ORIGINS` | `http://localhost:3000,...` | Comma-separated CORS origins |
| `ACTIVE_MODEL` | `efficientnet` | `cnn` \| `vgg16` \| `resnet50` \| `efficientnet` |
| `IMAGE_SIZE` | `224` | Input image dimension (pixels) |
| `CLASS_NAMES` | `glioma,meningioma,notumor,pituitary` | Comma-separated class labels |
| `SAVED_MODELS_DIR` | `./saved_models` | Where trained weights are stored |
| `DATASET_RAW_DIR` | `./dataset/raw` | Raw MRI image dataset |
| `DATASET_PROCESSED_DIR` | `./dataset/processed` | Preprocessed images |
| `GRADCAM_OUTPUT_DIR` | `./gradcam_output` | Grad-CAM PNG output directory |
| `LOG_LEVEL` | `INFO` | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` |
| `LOG_DIR` | `./logs` | Log file directory |

### Backend (`backend/.env`)

| Variable | Default | Description |
|---|---|---|
| `PORT` | `5000` | Express listen port |
| `NODE_ENV` | `development` | `development` \| `production` \| `test` |
| `FRONTEND_URL` | `http://localhost:3000` | CORS allowed origin |
| `UPLOAD_DIR` | `../uploads` | Multer upload directory |
| `DATASET_DIR` | `../dataset` | Shared dataset root |
| `MODEL_PATH` | `./models/edn_svm.json` | EDN-SVM model JSON path |
| `DB_PATH` | `./database/brain_tumor.db` | SQLite database file |
| `AI_SERVICE_URL` | `http://localhost:8000` | AI service base URL |
| `LOG_LEVEL` | `info` | Winston log level |

### Frontend (`frontend/.env.local`)

| Variable | Default | Description |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:5000` | Backend API base URL |
| `VITE_AI_SERVICE_URL` | `http://localhost:8000` | AI service base URL |
| `VITE_APP_NAME` | `Brain Tumour Detection` | App display name |
| `VITE_ENABLE_GRADCAM` | `true` | Show Grad-CAM heatmap panel |
| `VITE_ENABLE_COMPARISON` | `true` | Show model comparison tab |

---

## Makefile targets

```
make setup              Bootstrap all three environments (first-time only)
make setup-ai           Create Python venv and install AI service deps
make setup-backend      npm ci for backend, copy .env
make setup-frontend     npm ci for frontend, copy .env.local

make dev                Start all services in a tmux session
make dev-ai             AI service only  (port 8000, --reload)
make dev-backend        Backend only     (port 5000, nodemon)
make dev-frontend       Frontend only    (port 3000, Vite HMR)

make test               Run all test suites
make test-ai            pytest (ai-service/tests/)
make test-backend       Jest  (backend/tests/)
make test-ai-coverage   pytest with HTML coverage report

make build              Build all production artefacts
make build-frontend     Vite build → frontend/dist/

make docker-build       docker compose build --no-cache
make docker-up          Build and start all containers (detached)
make docker-down        Stop and remove containers
make docker-restart     Restart all containers
make docker-logs        Tail logs from all containers
make docker-logs-ai     Tail AI service logs
make docker-logs-backend Tail backend logs
make docker-ps          Show container status
make docker-prune       Remove stopped containers and dangling images

make env-check          Verify all .env files exist
make migrate            Run SQLite database migrations
make clean              Remove build artefacts and logs
make clean-all          Deep clean (removes .venv and node_modules)
```

---

## Project structure

```
BRAINTUMOR/
├── ai-service/               # Python / FastAPI / TensorFlow
│   ├── app/
│   │   ├── api/routes.py     # REST endpoints
│   │   ├── core/             # config, logging
│   │   ├── models/           # architectures, train, predict, evaluate
│   │   ├── preprocessing/    # image pipeline
│   │   └── utils/gradcam.py  # Grad-CAM explainability
│   ├── dataset/              # raw/ and processed/ MRI images
│   ├── saved_models/         # trained Keras weights
│   ├── tests/                # pytest suite
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── setup_env.ps1         # Windows bootstrap
│   └── setup_env.sh          # Linux/macOS bootstrap
│
├── backend/                  # Node.js / Express / SQLite
│   ├── api/                  # route handlers
│   ├── database/             # schema SQL, migrations, db.js
│   ├── middleware/           # upload, error handler, validate
│   ├── pipeline/             # preprocessing, segmentation, features, classifier
│   ├── server.js
│   ├── config.js
│   └── .env.example
│
├── frontend/                 # React 18 / Vite / Tailwind
│   ├── src/
│   ├── vite.config.js
│   └── .env.example
│
├── docker/
│   ├── docker-compose.yml
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── nginx.conf
│
├── Makefile
└── README.md
```

---

## Training a model

With the AI service running locally:

```bash
# Train EfficientNetB3 (default — recommended)
curl -X POST http://localhost:8000/api/v1/train \
  -H "Content-Type: application/json" \
  -d '{"model_name": "efficientnet", "epochs": 30, "batch_size": 32}'

# Train the lightweight custom CNN
curl -X POST http://localhost:8000/api/v1/train \
  -d '{"model_name": "cnn", "epochs": 50, "fine_tune": false}'
```

Dataset must be placed in `ai-service/dataset/raw/` following Keras directory layout:

```
dataset/raw/
    glioma/       ← MRI images for class "glioma"
    meningioma/
    notumor/
    pituitary/
```

## Running inference

```bash
curl -X POST http://localhost:8000/api/v1/predict \
  -F "image=@path/to/mri_scan.jpg" \
  -F "model_name=efficientnet" \
  -F "generate_gradcam=true"
```

---

## Running tests

```bash
make test               # all suites

# Individual suites
make test-ai            # 81 Python tests
make test-backend       # Jest tests
make test-ai-coverage   # with HTML coverage report → ai-service/htmlcov/
```
