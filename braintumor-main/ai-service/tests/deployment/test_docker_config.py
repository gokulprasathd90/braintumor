"""
tests/deployment/test_docker_config.py
───────────────────────────────────────
Validates Docker configuration files are well-formed and follow required
conventions (non-root, healthchecks, required labels, etc.).

Runs with standard pytest — no Docker daemon required.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# Repo root is 2 levels up: ai-service/tests/deployment → repo root
REPO_ROOT = Path(__file__).resolve().parents[3]
DOCKER_DIR = REPO_ROOT / "docker"
AI_DOCKERFILE = REPO_ROOT / "ai-service" / "Dockerfile"


# ─── Helpers ─────────────────────────────────────────────────────────────────

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ═════════════════════════════════════════════════════════════════════════════
# AI Service Dockerfile
# ═════════════════════════════════════════════════════════════════════════════

class TestAiServiceDockerfile:
    """Validates ai-service/Dockerfile."""

    @pytest.fixture(autouse=True)
    def content(self):
        assert AI_DOCKERFILE.exists(), "ai-service/Dockerfile not found"
        self._content = read(AI_DOCKERFILE)

    @property
    def c(self) -> str:
        return self._content

    def test_is_multi_stage(self):
        """Must use at least two FROM stages."""
        stages = re.findall(r"^FROM\s+", self.c, re.MULTILINE)
        assert len(stages) >= 2, "Dockerfile must have at least 2 stages (builder + runtime)"

    def test_has_builder_stage(self):
        assert re.search(r"FROM\s+\S+\s+AS\s+builder", self.c, re.IGNORECASE), \
            "Missing 'AS builder' stage"

    def test_has_runtime_stage(self):
        assert re.search(r"FROM\s+\S+\s+AS\s+runtime", self.c, re.IGNORECASE), \
            "Missing 'AS runtime' stage"

    def test_non_root_user(self):
        """Must switch to a non-root user."""
        assert "USER appuser" in self.c, "Must switch to non-root USER appuser"

    def test_non_root_group_created(self):
        assert "appgroup" in self.c, "Must create appgroup for non-root operation"

    def test_healthcheck_defined(self):
        assert "HEALTHCHECK" in self.c, "HEALTHCHECK instruction is required"

    def test_healthcheck_uses_curl_or_python(self):
        assert re.search(r"HEALTHCHECK.*\n.*CMD\s+(curl|python)", self.c, re.DOTALL) or \
               re.search(r"CMD curl|CMD python", self.c), \
            "HEALTHCHECK CMD must use curl or python"

    def test_stopsignal_defined(self):
        assert "STOPSIGNAL SIGTERM" in self.c, "STOPSIGNAL SIGTERM required for graceful shutdown"

    def test_oci_labels_present(self):
        required_labels = [
            "org.opencontainers.image.title",
            "org.opencontainers.image.version",
            "org.opencontainers.image.created",
            "org.opencontainers.image.revision",
        ]
        for label in required_labels:
            assert label in self.c, f"OCI label '{label}' is missing"

    def test_build_date_arg(self):
        assert "ARG BUILD_DATE" in self.c, "ARG BUILD_DATE must be defined for reproducible builds"

    def test_git_commit_arg(self):
        assert "ARG GIT_COMMIT" in self.c, "ARG GIT_COMMIT must be defined for traceability"

    def test_no_apt_cache_left(self):
        """apt-get must clean up after itself."""
        # Every apt-get install block should be followed by rm -rf /var/lib/apt/lists/*
        apt_installs = len(re.findall(r"apt-get install", self.c))
        cleanups = len(re.findall(r"rm -rf /var/lib/apt/lists/\*", self.c))
        assert cleanups >= apt_installs, \
            f"Every apt-get install ({apt_installs}) must have a corresponding cleanup ({cleanups})"

    def test_pythonunbuffered_set(self):
        assert "PYTHONUNBUFFERED=1" in self.c, \
            "PYTHONUNBUFFERED=1 required to avoid buffered stdout in containers"

    def test_entrypoint_uses_tini(self):
        assert "tini" in self.c.lower(), \
            "tini should be used as PID 1 for proper signal handling"

    def test_exposes_correct_port(self):
        assert "EXPOSE 8000" in self.c, "AI service must EXPOSE port 8000"

    def test_production_env_default(self):
        assert "AI_SERVICE_ENV=production" in self.c, \
            "AI_SERVICE_ENV should default to production in the image"

    def test_debug_off_by_default(self):
        assert "AI_SERVICE_DEBUG=false" in self.c, \
            "AI_SERVICE_DEBUG must default to false in the production image"


# ═════════════════════════════════════════════════════════════════════════════
# Backend Dockerfile
# ═════════════════════════════════════════════════════════════════════════════

class TestBackendDockerfile:
    """Validates docker/Dockerfile.backend."""

    @pytest.fixture(autouse=True)
    def content(self):
        path = DOCKER_DIR / "Dockerfile.backend"
        assert path.exists(), "docker/Dockerfile.backend not found"
        self._content = read(path)

    @property
    def c(self) -> str:
        return self._content

    def test_multi_stage(self):
        stages = re.findall(r"^FROM\s+", self._content, re.MULTILINE)
        assert len(stages) >= 2

    def test_non_root_user(self):
        assert "USER appuser" in self._content

    def test_healthcheck(self):
        assert "HEALTHCHECK" in self._content

    def test_stopsignal(self):
        assert "STOPSIGNAL" in self._content

    def test_oci_labels(self):
        assert "org.opencontainers.image.title" in self._content

    def test_production_node_env(self):
        assert "NODE_ENV=production" in self._content

    def test_exposes_port_5000(self):
        assert "EXPOSE 5000" in self._content


# ═════════════════════════════════════════════════════════════════════════════
# Frontend Dockerfile
# ═════════════════════════════════════════════════════════════════════════════

class TestFrontendDockerfile:
    """Validates docker/Dockerfile.frontend."""

    @pytest.fixture(autouse=True)
    def content(self):
        path = DOCKER_DIR / "Dockerfile.frontend"
        assert path.exists(), "docker/Dockerfile.frontend not found"
        self._content = read(path)

    @property
    def c(self) -> str:
        return self._content

    def test_multi_stage(self):
        stages = re.findall(r"^FROM\s+", self._content, re.MULTILINE)
        assert len(stages) >= 2

    def test_builder_stage(self):
        assert re.search(r"FROM\s+node.*AS\s+builder", self._content, re.IGNORECASE)

    def test_runtime_uses_nginx(self):
        assert re.search(r"FROM\s+nginx.*AS\s+runtime", self._content, re.IGNORECASE)

    def test_non_root_user(self):
        assert "USER appuser" in self._content

    def test_healthcheck(self):
        assert "HEALTHCHECK" in self._content

    def test_vite_build_args(self):
        required_args = ["VITE_API_BASE_URL", "VITE_AI_SERVICE_URL", "VITE_APP_NAME"]
        for arg in required_args:
            assert f"ARG {arg}" in self._content, f"Missing ARG {arg}"

    def test_non_root_port(self):
        """Frontend uses port 8080 (non-root nginx)."""
        assert "EXPOSE 8080" in self._content, "Frontend must EXPOSE 8080 for non-root nginx"


# ═════════════════════════════════════════════════════════════════════════════
# Docker Compose files
# ═════════════════════════════════════════════════════════════════════════════

class TestDockerCompose:
    """Validates Docker Compose configuration files."""

    def _read(self, name: str) -> str:
        path = DOCKER_DIR / name
        assert path.exists(), f"{name} not found in docker/"
        return read(path)

    def test_base_compose_exists(self):
        assert (DOCKER_DIR / "docker-compose.yml").exists()

    def test_dev_compose_exists(self):
        assert (DOCKER_DIR / "docker-compose.dev.yml").exists()

    def test_prod_compose_exists(self):
        assert (DOCKER_DIR / "docker-compose.prod.yml").exists()

    def test_override_compose_exists(self):
        assert (DOCKER_DIR / "docker-compose.override.yml").exists()

    def test_base_compose_has_all_services(self):
        content = self._read("docker-compose.yml")
        for service in ("ai-service", "backend", "frontend"):
            assert f"{service}:" in content, f"Service '{service}' missing from docker-compose.yml"

    def test_base_compose_has_healthchecks(self):
        content = self._read("docker-compose.yml")
        # All services should have healthcheck
        assert content.count("healthcheck:") >= 3, \
            "All three services must have healthcheck defined in base compose"

    def test_base_compose_has_named_volumes(self):
        content = self._read("docker-compose.yml")
        required_volumes = ["models_volume", "dataset_volume", "db_volume", "uploads_volume"]
        for vol in required_volumes:
            assert vol in content, f"Named volume '{vol}' missing from docker-compose.yml"

    def test_base_compose_has_networks(self):
        content = self._read("docker-compose.yml")
        assert "app_network" in content

    def test_base_compose_service_depends_on(self):
        content = self._read("docker-compose.yml")
        # backend should depend on ai-service
        assert "depends_on" in content, "Service dependencies not configured"

    def test_prod_compose_has_resource_limits(self):
        content = self._read("docker-compose.prod.yml")
        assert "resources:" in content, "Production compose must define resource limits"
        assert "limits:" in content
        assert "memory:" in content
        assert "cpus:" in content

    def test_prod_compose_has_secrets(self):
        content = self._read("docker-compose.prod.yml")
        assert "secrets:" in content, "Production compose must define Docker secrets"

    def test_prod_compose_restart_always(self):
        content = self._read("docker-compose.prod.yml")
        assert "restart: always" in content, \
            "Production containers must use restart: always"

    def test_prod_compose_security_options(self):
        content = self._read("docker-compose.prod.yml")
        assert "no-new-privileges" in content, \
            "Production containers must set no-new-privileges security option"

    def test_ai_service_inter_service_url(self):
        content = self._read("docker-compose.yml")
        assert "http://ai-service:8000" in content, \
            "Backend must reference ai-service by service name (not localhost)"


# ═════════════════════════════════════════════════════════════════════════════
# Nginx configuration
# ═════════════════════════════════════════════════════════════════════════════

class TestNginxConfig:
    """Validates nginx configuration files."""

    def test_nginx_conf_exists(self):
        assert (DOCKER_DIR / "nginx.conf").exists()

    def test_nginx_dir_default_conf_exists(self):
        assert (DOCKER_DIR / "nginx" / "default.conf").exists()

    def test_nginx_conf_has_gzip(self):
        content = read(DOCKER_DIR / "nginx.conf")
        assert "gzip" in content.lower()

    def test_nginx_conf_has_security_headers(self):
        content = read(DOCKER_DIR / "nginx.conf")
        assert "X-Content-Type-Options" in content
        assert "X-Frame-Options" in content

    def test_nginx_conf_server_tokens_off(self):
        content = read(DOCKER_DIR / "nginx.conf")
        assert "server_tokens off" in content, "server_tokens must be off"

    def test_nginx_conf_health_probe(self):
        content = read(DOCKER_DIR / "nginx.conf")
        assert "nginx-health" in content, "/nginx-health probe endpoint required"

    def test_nginx_conf_spa_fallback(self):
        content = read(DOCKER_DIR / "nginx.conf")
        assert "try_files" in content and "index.html" in content, \
            "SPA fallback routing to index.html required"

    def test_nginx_reverse_proxy_conf_has_upstream(self):
        content = read(DOCKER_DIR / "nginx" / "default.conf")
        assert "upstream backend_upstream" in content
        assert "upstream ai_service_upstream" in content

    def test_nginx_reverse_proxy_api_location(self):
        content = read(DOCKER_DIR / "nginx" / "default.conf")
        assert "location /api/" in content, "Must proxy /api/ to backend"

    def test_nginx_reverse_proxy_ai_location(self):
        content = read(DOCKER_DIR / "nginx" / "default.conf")
        assert "location /ai/" in content, "Must proxy /ai/ to ai-service"

    def test_nginx_https_ready(self):
        """HTTPS server block must exist (commented out is OK)."""
        content = read(DOCKER_DIR / "nginx" / "default.conf")
        assert "443" in content or "ssl" in content.lower(), \
            "HTTPS/TLS configuration should be present (even if commented)"

    def test_nginx_rate_limit_zones(self):
        content = read(DOCKER_DIR / "nginx" / "nginx.conf")
        assert "limit_req_zone" in content, "Rate limiting zones required in nginx.conf"


# ═════════════════════════════════════════════════════════════════════════════
# Entrypoint scripts
# ═════════════════════════════════════════════════════════════════════════════

class TestEntrypointScripts:
    """Validates docker entrypoint shell scripts."""

    def test_ai_entrypoint_exists(self):
        assert (DOCKER_DIR / "scripts" / "ai-entrypoint.sh").exists()

    def test_backend_entrypoint_exists(self):
        assert (DOCKER_DIR / "scripts" / "backend-entrypoint.sh").exists()

    def test_ai_entrypoint_exec_at_end(self):
        content = read(DOCKER_DIR / "scripts" / "ai-entrypoint.sh")
        assert "exec \"$@\"" in content, \
            "Entrypoint must exec CMD to transfer PID 1 to the application"

    def test_backend_entrypoint_exec_at_end(self):
        content = read(DOCKER_DIR / "scripts" / "backend-entrypoint.sh")
        assert "exec \"$@\"" in content

    def test_ai_entrypoint_jwt_check(self):
        content = read(DOCKER_DIR / "scripts" / "ai-entrypoint.sh")
        assert "JWT_SECRET_KEY" in content, \
            "AI entrypoint must validate JWT_SECRET_KEY strength in production"

    def test_ai_entrypoint_set_e(self):
        content = read(DOCKER_DIR / "scripts" / "ai-entrypoint.sh")
        assert "set -e" in content, "Entrypoint must use 'set -e' for error handling"
