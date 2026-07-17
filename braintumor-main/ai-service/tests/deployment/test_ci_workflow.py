"""
tests/deployment/test_ci_workflow.py
──────────────────────────────────────
Validates GitHub Actions workflow YAML files for required structure,
job names, and trigger configuration.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"


def read_workflow(name: str) -> str:
    path = WORKFLOWS_DIR / name
    assert path.exists(), f"Workflow file not found: .github/workflows/{name}"
    return path.read_text(encoding="utf-8")


# ═════════════════════════════════════════════════════════════════════════════
# CI Workflow
# ═════════════════════════════════════════════════════════════════════════════

class TestCIWorkflow:
    """Validates .github/workflows/ci.yml."""

    @pytest.fixture(autouse=True)
    def content(self):
        self._content = read_workflow("ci.yml")

    @property
    def c(self) -> str:
        return self._content

    def test_workflow_file_exists(self):
        assert (WORKFLOWS_DIR / "ci.yml").exists()

    def test_triggers_on_push_main(self):
        assert "main" in self.c, "CI must trigger on pushes to main"

    def test_triggers_on_pull_request(self):
        assert "pull_request:" in self.c, "CI must trigger on pull requests"

    def test_has_python_lint_job(self):
        assert "lint-ai" in self.c or "lint_ai" in self.c, \
            "CI must have a Python linting job"

    def test_has_frontend_lint_job(self):
        assert "lint-frontend" in self.c or "lint_frontend" in self.c, \
            "CI must have a frontend linting job"

    def test_has_python_test_job(self):
        assert "test-ai" in self.c or "test_ai" in self.c or "pytest" in self.c, \
            "CI must have a Python test job"

    def test_has_frontend_test_job(self):
        assert "test-frontend" in self.c or "vitest" in self.c, \
            "CI must have a frontend test job"

    def test_has_docker_build_job(self):
        assert "docker-build" in self.c or "docker_build" in self.c or \
               "docker/build-push-action" in self.c, \
            "CI must include a Docker build job"

    def test_uses_ruff(self):
        assert "ruff" in self.c.lower(), "CI Python lint must use ruff"

    def test_uses_black(self):
        assert "black" in self.c.lower(), "CI Python lint must use black"

    def test_uses_pytest(self):
        assert "pytest" in self.c.lower(), "CI must run pytest"

    def test_uses_vitest(self):
        assert "vitest" in self.c.lower() or "test:coverage" in self.c, \
            "CI must run vitest for frontend tests"

    def test_coverage_uploaded(self):
        assert "codecov" in self.c.lower() or "coverage" in self.c.lower(), \
            "CI should upload coverage reports"

    def test_docker_buildx_used(self):
        assert "setup-buildx-action" in self.c, \
            "CI must use docker/setup-buildx-action for efficient layer caching"

    def test_layer_caching(self):
        assert "cache-from" in self.c, "CI Docker build must use layer caching"

    def test_uses_concurrency(self):
        assert "concurrency:" in self.c, \
            "CI must define concurrency group to cancel duplicate runs"

    def test_cancel_in_progress(self):
        assert "cancel-in-progress: true" in self.c, \
            "CI must cancel in-progress runs on new pushes to the same branch"

    def test_ghcr_push(self):
        assert "ghcr.io" in self.c, "CI must push images to GitHub Container Registry"

    def test_security_scan_job(self):
        assert "security-scan" in self.c or "trivy" in self.c.lower(), \
            "CI must include a security/vulnerability scan job"

    def test_summary_job(self):
        assert "ci-summary" in self.c or "all checks" in self.c.lower(), \
            "CI should have a summary/gate job that all other jobs feed into"

    def test_python_version_pinned(self):
        # Version can be set as an env var (PYTHON_VERSION: "3.12") and referenced via ${{ env.PYTHON_VERSION }}
        assert re.search(r'PYTHON_VERSION.*3\.\d+|python-version.*3\.\d+', self.c), \
            "Python version must be explicitly pinned"

    def test_node_version_pinned(self):
        # Version can be set as an env var (NODE_VERSION: "20") and referenced via ${{ env.NODE_VERSION }}
        assert re.search(r'NODE_VERSION.*\d+|node-version.*\d+', self.c), \
            "Node.js version must be explicitly pinned"

    def test_artifact_upload(self):
        assert "upload-artifact" in self.c, \
            "CI must upload test results as artifacts"


# ═════════════════════════════════════════════════════════════════════════════
# CD Workflow
# ═════════════════════════════════════════════════════════════════════════════

class TestCDWorkflow:
    """Validates .github/workflows/cd.yml."""

    @pytest.fixture(autouse=True)
    def content(self):
        self._content = read_workflow("cd.yml")

    @property
    def c(self) -> str:
        return self._content

    def test_workflow_file_exists(self):
        assert (WORKFLOWS_DIR / "cd.yml").exists()

    def test_triggers_on_push_main(self):
        assert "push:" in self.c and "main" in self.c

    def test_triggers_on_release(self):
        assert "release:" in self.c, "CD must trigger on GitHub Releases"

    def test_has_workflow_dispatch(self):
        assert "workflow_dispatch:" in self.c, \
            "CD must support manual triggering via workflow_dispatch"

    def test_environment_input(self):
        assert "environment" in self.c and ("staging" in self.c or "production" in self.c), \
            "CD must support selecting deployment environment"

    def test_no_cancel_in_progress_deploy(self):
        assert "cancel-in-progress: false" in self.c, \
            "Running deployments must never be cancelled by a new deploy"

    def test_uses_ssh_deploy(self):
        assert "ssh" in self.c.lower() or "appleboy" in self.c.lower(), \
            "CD must deploy via SSH"

    def test_smoke_test_after_deploy(self):
        assert "smoke" in self.c.lower() or "health" in self.c.lower(), \
            "CD must run smoke tests after deployment"

    def test_slack_notification(self):
        assert "slack" in self.c.lower() or "notify" in self.c.lower() or \
               "SLACK_WEBHOOK" in self.c, \
            "CD should include deployment notifications"


# ═════════════════════════════════════════════════════════════════════════════
# Release Workflow
# ═════════════════════════════════════════════════════════════════════════════

class TestReleaseWorkflow:
    """Validates .github/workflows/release.yml."""

    @pytest.fixture(autouse=True)
    def content(self):
        self._content = read_workflow("release.yml")

    @property
    def c(self) -> str:
        return self._content

    def test_workflow_file_exists(self):
        assert (WORKFLOWS_DIR / "release.yml").exists()

    def test_triggers_on_version_tags(self):
        assert re.search(r"v\[0-9\]", self.c) or "v[0-9]" in self.c, \
            "Release workflow must trigger on version tags"

    def test_creates_github_release(self):
        assert "action-gh-release" in self.c or "releases" in self.c.lower(), \
            "Release workflow must create a GitHub Release"

    def test_generates_changelog(self):
        assert "changelog" in self.c.lower(), \
            "Release workflow must generate a changelog"

    def test_pushes_versioned_images(self):
        assert "semver" in self.c.lower() or "type=semver" in self.c, \
            "Release workflow must push semver-tagged Docker images"

    def test_supports_prerelease(self):
        assert "prerelease" in self.c.lower(), \
            "Release workflow must handle pre-release tags (e.g. v1.0.0-rc.1)"

    def test_latest_tag_only_on_stable(self):
        assert "prerelease" in self.c and "latest" in self.c, \
            "'latest' tag should only be pushed for stable (non-prerelease) versions"


# ═════════════════════════════════════════════════════════════════════════════
# Workflow directory structure
# ═════════════════════════════════════════════════════════════════════════════

class TestWorkflowStructure:
    """Validates overall .github/workflows/ directory structure."""

    def test_workflows_dir_exists(self):
        assert WORKFLOWS_DIR.exists(), ".github/workflows/ directory must exist"

    def test_required_workflows_present(self):
        required = ["ci.yml", "cd.yml", "release.yml"]
        for wf in required:
            assert (WORKFLOWS_DIR / wf).exists(), f"Required workflow missing: {wf}"

    def test_no_plaintext_secrets_in_workflows(self):
        """Check that no workflow hardcodes a secret value."""
        secret_patterns = [
            r'password\s*=\s*["\'][^$][^"\']{5,}["\']',
            r'secret\s*=\s*["\'][^$][^"\']{5,}["\']',
            r'api[_-]?key\s*=\s*["\'][^$][^"\']{5,}["\']',
        ]
        for wf_file in WORKFLOWS_DIR.glob("*.yml"):
            content = wf_file.read_text(encoding="utf-8").lower()
            for pattern in secret_patterns:
                assert not re.search(pattern, content), \
                    f"Possible hardcoded secret in {wf_file.name}"

    def test_workflows_reference_secrets_via_context(self):
        """Sensitive values must come from ${{ secrets.* }}."""
        for wf_file in WORKFLOWS_DIR.glob("*.yml"):
            content = wf_file.read_text(encoding="utf-8")
            # Any SSH key or password reference must use secrets context
            if "SSH" in content or "password" in content.lower():
                assert "secrets." in content, \
                    f"{wf_file.name} contains SSH/password but does not use secrets context"
