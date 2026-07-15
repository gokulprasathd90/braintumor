# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | ✅ Active support |
| < 1.0   | ❌ No longer supported |

---

## Reporting a Vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

If you discover a security issue, please report it privately so we can address it before public disclosure.

### How to Report

1. **Email:** Send a report to the maintainers via the contact details on the repository profile, or open a [GitHub Security Advisory](https://github.com/your-org/brain-tumor-detection/security/advisories/new) (preferred).
2. **Subject line:** Use the format `[SECURITY] Brief description of the issue`
3. **Include in your report:**
   - A description of the vulnerability and its potential impact
   - Steps to reproduce or a proof-of-concept
   - Affected versions
   - Any suggested mitigation or fix, if known

### Response Timeline

| Action | Target timeframe |
|--------|-----------------|
| Acknowledgement of report | Within 48 hours |
| Initial assessment | Within 5 business days |
| Fix developed and tested | Within 14 days (critical), 30 days (others) |
| Coordinated public disclosure | After fix is released |

We will keep you informed of progress throughout. If you do not receive an acknowledgement within 48 hours, please follow up.

---

## Disclosure Policy

We follow coordinated (responsible) disclosure:

1. Reporter submits details privately.
2. Maintainers confirm the issue and develop a fix.
3. A patched release is prepared and staged.
4. A CVE is requested if the severity warrants it.
5. The patched release is published.
6. A security advisory is published on GitHub.
7. The reporter is credited (unless they prefer anonymity).

We ask reporters to allow reasonable time for a fix before any public disclosure.

---

## Scope

### In Scope

- Authentication and authorisation bypass (JWT, RBAC)
- Remote code execution via image upload or API parameters
- SQL injection or path traversal via API inputs
- Privilege escalation between user roles
- Secrets or credentials exposed in API responses, logs, or error messages
- Denial-of-service vulnerabilities in the AI inference pipeline
- Dependency vulnerabilities with direct exploitability in this project

### Out of Scope

- Vulnerabilities in third-party services not under our control
- Issues requiring physical access to the server
- Social engineering attacks
- Scanner-reported findings without evidence of exploitability
- Rate limiting bypass without demonstrated harm
- Missing security headers on development builds (only production matters)

---

## Security Architecture

### Authentication

- JWT-based authentication with short-lived access tokens (30 min) and rotating refresh tokens (7 days)
- Tokens signed with HS256; secret key loaded from environment — never hardcoded
- bcrypt password hashing with a minimum cost factor of 12

### Authorisation

- Role-based access control (RBAC) with four roles: Admin, Researcher, Operator, Viewer
- Each API endpoint declares the minimum required role via a FastAPI dependency
- Role checks are enforced server-side — the frontend role display is cosmetic only

### Rate Limiting

- SlowAPI rate limiting applied per-endpoint and per-IP
- Default limits: 10 requests/minute on auth endpoints, 60 requests/minute on inference

### Input Validation

- All uploaded images are validated for MIME type, file extension, and maximum size before processing
- Pydantic models enforce strict types and value ranges on all API request bodies
- File paths are never constructed from user input

### Dependency Management

- Python dependencies are pinned to exact versions in `requirements.txt`
- Node dependencies use exact versions in `package-lock.json`
- GitHub Actions CI runs `pip-audit` and `npm audit` on every pull request

### Secrets Management

- All secrets are loaded from environment variables — never committed to version control
- Docker secrets integration is available for production deployments (see `docker/docker-compose.prod.yml`)
- `.env` files are listed in `.gitignore`

### Audit Logging

- All authentication events (login, logout, token refresh, failed login, account lockout) are written to an append-only JSONL audit log
- Audit log entries include timestamp, user ID, IP address, user agent, and outcome

---

## Known Security Considerations

### Medical Disclaimer

This software is for research and educational purposes only. It must not be used to make clinical decisions. Predictions from the model are not medical diagnoses. See [LICENSE](LICENSE) for the full disclaimer.

### AI Model Security

- Model weight files are loaded from a trusted local path (`SAVED_MODELS_DIR`) — never from user-supplied URLs
- Grad-CAM output images are served as base64-encoded data URLs — not written to user-accessible file system paths in production

### File Upload Security

- Accepted MIME types: `image/jpeg`, `image/png`, `image/webp` only
- Maximum upload size: 10 MB
- Uploaded files are processed in memory and not persisted to disk after inference

---

## Security Updates

Security patches are released as patch versions (e.g., `1.0.1`) and noted in [CHANGELOG.md](CHANGELOG.md) with a `### Security` section. Subscribe to [GitHub releases](https://github.com/your-org/brain-tumor-detection/releases) to be notified of security updates.
