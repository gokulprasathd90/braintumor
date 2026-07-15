# Installation Guide

Brain Tumour Detection — step-by-step installation for every supported platform.

---

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Install Prerequisites](#install-prerequisites)
3. [Clone the Repository](#clone-the-repository)
4. [Option A — Docker (Recommended)](#option-a--docker-recommended)
5. [Option B — Local Development](#option-b--local-development)
   - [AI Service (Python)](#ai-service-python)
   - [Backend (Node.js)](#backend-nodejs)
   - [Frontend (React)](#frontend-react)
6. [Environment Configuration](#environment-configuration)
7. [Database Setup](#database-setup)
8. [Verify the Installation](#verify-the-installation)
9. [GPU Support (Optional)](#gpu-support-optional)
10. [Uninstall](#uninstall)

---

## System Requirements

| Resource | Minimum | Recommended |
|---|---|---|
| CPU | 4 cores | 8+ cores |
| RAM | 8 GB | 16 GB |
| Disk | 10 GB free | 30 GB free |
| GPU | — (CPU inference works) | NVIDIA with 4 GB VRAM |
| OS | Windows 10 / macOS 12 / Ubuntu 20.04 | Ubuntu 22.04 LTS |
| Python | 3.12 | 3.12 |
| Node.js | 20 LTS | 20 LTS |
| Docker | 24.x | 25.x |

---

## Install Prerequisites

### Python 3.12

**Windows:**
```powershell
winget install Python.Python.3.12
# or download from https://www.python.org/downloads/
```

**macOS:**
```bash
brew install python@3.12
```

**Ubuntu/Debian:**
```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.12 python3.12-venv python3.12-dev
```

### Node.js 20 LTS

**Windows / macOS / Linux:**
```bash
# Using nvm (recommended)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
nvm install 20
nvm use 20
```

**Windows (winget):**
```powershell
winget install OpenJS.NodeJS.LTS
```

### Docker

- **Windows / macOS:** Install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- **Linux:**
  ```bash
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker $USER
  newgrp docker
  ```

Verify Docker is working:
```bash
docker --version          # Docker version 24.x or later
docker compose version    # Docker Compose version v2.x or later
```

---

## Clone the Repository

```bash
git clone https://github.com/your-org/brain-tumor-detection.git
cd brain-tumor-detection
```

---

## Option A — Docker (Recommended)

Docker is the simplest way to get all three services running with correct network wiring.

### 1. Copy environment templates

```bash
cp ai-service/.env.example  ai-service/.env
cp backend/.env.example     backend/.env
cp frontend/.env.example    frontend/.env.local
```

**Windows (PowerShell):**
```powershell
Copy-Item ai-service\.env.example  ai-service\.env
Copy-Item backend\.env.example     backend\.env
Copy-Item frontend\.env.example    frontend\.env.local
```

### 2. Set a strong JWT secret

```bash
# Linux / macOS
echo "JWT_SECRET_KEY=$(openssl rand -hex 32)" >> ai-service/.env

# Windows PowerShell
$secret = -join ((48..57) + (97..102) | Get-Random -Count 64 | ForEach-Object {[char]$_})
Add-Content ai-service\.env "JWT_SECRET_KEY=$secret"
```

### 3. Build and start

```bash
docker compose -f docker/docker-compose.yml up --build -d
```

Or with Make:
```bash
make docker-up
```

### 4. Wait for health checks

```bash
docker compose -f docker/docker-compose.yml ps
# All services should show "healthy" after ~90 seconds (TF model load)
```

### 5. Access the application

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:5000 |
| AI Service Swagger | http://localhost:8000/docs |
| AI Service ReDoc | http://localhost:8000/redoc |

---

## Option B — Local Development

### AI Service (Python)

#### 1. Create virtual environment

```bash
cd ai-service

# Linux / macOS
python3.12 -m venv .venv
source .venv/bin/activate

# Windows PowerShell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Or use the provided bootstrap script:

```bash
# Linux / macOS
bash setup_env.sh

# Windows
.\setup_env.ps1
```

#### 2. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

For development tools (pytest, ruff, black, isort):
```bash
pip install -r requirements-dev.txt
```

#### 3. Configure environment

```bash
cp .env.example .env
# Edit .env — at minimum set JWT_SECRET_KEY to a long random string
```

#### 4. Start the AI service

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Confirm it is running:
```bash
curl http://localhost:8000/api/v1/health
```

---

### Backend (Node.js)

#### 1. Install dependencies

```bash
cd backend
npm ci
```

#### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — set AI_SERVICE_URL to http://localhost:8000
```

#### 3. Run migrations

```bash
node database/migrate.js
```

#### 4. Start the backend

```bash
npm run dev
```

Confirm it is running:
```bash
curl http://localhost:5000/api/health
```

---

### Frontend (React)

#### 1. Install dependencies

```bash
cd frontend
npm ci
```

#### 2. Configure environment

```bash
cp .env.example .env.local
# Edit .env.local — defaults work if backend runs on port 5000
```

#### 3. Start the development server

```bash
npm run dev
```

Open http://localhost:3000 in your browser.

---

## Environment Configuration

All three services use `.env` files. Never commit `.env` files — they are listed in `.gitignore`.

### Critical values to change before production

| File | Variable | Why |
|---|---|---|
| `ai-service/.env` | `JWT_SECRET_KEY` | Must be a long random string; default is insecure |
| `ai-service/.env` | `AI_SERVICE_ENV` | Set to `production` |
| `ai-service/.env` | `AI_SERVICE_DEBUG` | Set to `false` |
| `ai-service/.env` | `BCRYPT_ROUNDS` | Keep at `12` or higher |
| `backend/.env` | `NODE_ENV` | Set to `production` |

See the [README environment variables table](../README.md#environment-variables) for all options.

---

## Database Setup

The backend uses SQLite. Run migrations to create the schema:

```bash
cd backend
node database/migrate.js
```

This creates `backend/database/brain_tumor.db`. The file is excluded from version control.

---

## Verify the Installation

Run the full test suite to confirm everything works:

```bash
# From the project root
make test

# Or individually:
cd ai-service && python -m pytest tests/ -v
cd backend     && npm test
cd frontend    && npm test
```

Expected results:
- AI Service: **1,100+ tests passing**
- Backend: **112+ tests passing**
- Frontend: **280+ tests passing**

---

## GPU Support (Optional)

The AI service runs on CPU by default. For GPU acceleration:

### Check NVIDIA GPU availability

```bash
nvidia-smi
```

### Install CUDA toolkit

TensorFlow 2.20 requires **CUDA 12.x** and **cuDNN 9.x**.

Follow the official guide: https://www.tensorflow.org/install/pip#linux_setup

### Docker GPU support

Install the NVIDIA Container Toolkit:
```bash
distribution=$(. /etc/os-release; echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/libnvidia-container/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt update && sudo apt install -y nvidia-container-toolkit
sudo systemctl restart docker
```

Then add GPU resources to the AI service in `docker/docker-compose.override.yml`:
```yaml
services:
  ai-service:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

---

## Uninstall

### Docker

```bash
# Stop and remove containers + volumes
docker compose -f docker/docker-compose.yml down -v

# Remove Docker images
docker rmi $(docker images "brain-tumor*" -q)
```

### Local

```bash
# Remove Python virtual environment
rm -rf ai-service/.venv

# Remove Node modules
rm -rf backend/node_modules
rm -rf frontend/node_modules

# Remove generated data
rm -rf ai-service/saved_models/*
rm -rf ai-service/dataset/processed/*
rm -rf ai-service/logs/*
rm -rf backend/database/brain_tumor.db
rm -rf uploads/*
```
