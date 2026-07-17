# Authentication & Security Architecture

This document describes the design, implementation, and deployment recommendations for the security and authentication system in the Brain Tumour Detection AI Service.

---

## 1. Security Model & RBAC

The platform utilizes Role-Based Access Control (RBAC) to enforce fine-grained permissions. Access is granted based on the user's role.

### Role Hierarchy
Roles are ranked from highest to lowest privilege. A higher role inherits all permissions of the roles below it:

```
  ┌──────────────┐
  │    Admin     │ (Full control, dataset preparation, models, users)
  └──────┬───────┘
         │
  ┌──────▼───────┐
  │  Researcher  │ (Training, experiments, Grad-CAM, metrics)
  └──────┬───────┘
         │
  ┌──────▼───────┐
  │   Operator   │ (Single/batch predictions, preprocessing, reload models)
  └──────┬───────┘
         │
  ┌──────▼───────┐
  │    Viewer    │ (Read-only dashboard, system metrics, experiments)
  └──────────────┘
```

### Role-to-Permissions Mapping

| Permission | Description | Viewer | Operator | Researcher | Admin |
|:---|:---|:---:|:---:|:---:|:---:|
| `dashboard:read` | View metrics dashboard | ✓ | ✓ | ✓ | ✓ |
| `metrics:read` | Query system/inference metrics | ✓ | ✓ | ✓ | ✓ |
| `experiment:read` | View training experiments | ✓ | ✓ | ✓ | ✓ |
| `model:read` | View model registry details | ✓ | ✓ | ✓ | ✓ |
| `predict:single` | Run single MRI prediction | | ✓ | ✓ | ✓ |
| `predict:batch` | Run batch/ZIP predictions | | ✓ | ✓ | ✓ |
| `preprocess:run` | Quality check and augmentations | | ✓ | ✓ | ✓ |
| `model:reload` | Hot-reload specific model weights | | ✓ | ✓ | ✓ |
| `train:read` | Check running job status | | | ✓ | ✓ |
| `train:start` | Launch new training job | | | ✓ | ✓ |
| `dataset:read` | View dataset metrics and info | | | ✓ | ✓ |
| `dataset:prepare`| Split dataset / prepare splits | | | | ✓ |
| `dataset:manage` | Advanced dataset management | | | | ✓ |
| `user:manage` | Create, delete, unlock accounts | | | | ✓ |
| `audit:read` | Read system audit trails | | | | ✓ |

---

## 2. JWT Lifecycle

Authentication is implemented using stateless JSON Web Tokens (JWT).

### Token Types & Characteristics
1. **Access Token**:
   - **Type**: `access`
   - **Lifespan**: 30 minutes (configurable via `access_token_expire_minutes`)
   - **Signature**: HS256 HMAC utilizing a strong server-side secret key
   - **Claims**: Includes standard claims: `sub` (user ID), `role`, `type`, `iat` (issued at), `exp` (expires at), and `jti` (unique token ID).

2. **Refresh Token**:
   - **Type**: `refresh`
   - **Lifespan**: 7 days (configurable via `refresh_token_expire_days`)
   - **Purpose**: Used exclusively at `/api/v1/auth/refresh` to obtain a new Access Token without prompting the user for credentials.

### Token Revocation (Logout)
- On calling `/api/v1/auth/logout`, the active `refresh_token` and `access_token` are added to a fast in-memory revocation store.
- Revoked tokens are immediately rejected by backend middleware for all subsequent requests.

### Client-Side Token Rotation & Auto-Refresh
- The frontend client stores the access and refresh tokens in `localStorage`.
- An automatic background scheduler in the React application checks the token's expiration claim (`exp`) and triggers a refresh request 2 minutes prior to expiry.
- If a request receives an HTTP `401 Unauthorized` response, the Axios response interceptor attempts to refresh the access token and retries the failed request seamlessly. If the refresh token is also expired or invalid, it triggers a logout and displays a **Session Expired** dialog.

---

## 3. Rate Limiting

To prevent brute-force attacks and denial-of-service, endpoints are guarded with slowapi rate limits:

| Endpoint | Limit | Purpose |
|:---|:---|:---|
| `POST /api/v1/auth/login` | 5 requests per minute | Prevents credential cracking |
| `POST /api/v1/predict` | 60 requests per minute | Limits inference compute abuse |
| `POST /api/v1/train/start` | 5 requests per minute | Prevents GPU/CPU exhaustion |
| `GET /api/v1/metrics/*` | 120 requests per minute | Protects dashboard database |
| `POST /api/v1/auth/refresh`| 20 requests per minute | Limits token rotation frequency |

*Clients exceeding these limits receive an **HTTP 429 Too Many Requests** response.*

---

## 4. Audit Logging

A secure audit logger records all security-critical system events in structured JSONL format inside `logs/audit/`.

### Events Recorded
- **Login Events**: Successful logins, logouts, and failed attempts (including IP and user agent).
- **Inference Events**: Prediction and batch prediction requests.
- **Model Modifications**: Weight reload actions.
- **Training Events**: Job start, completion, or failure.
- **Dataset Events**: Preparation and splitting.
- **Access Control**: Authorization failures (HTTP 403).

### Lockout Mechanism
After **5 consecutive failed login attempts**, the account is locked for **15 minutes** (customizable). Lockouts are audited and enforced at login.

---

## 5. Deployment Security Recommendations

For production environments, the following guidelines are strongly recommended:

1. **Enforce HTTPS**: Always run the API behind a reverse proxy (e.g., Nginx, Traefik) configured with TLS/SSL.
2. **Override Secrets**:
   - Change `JWT_SECRET_KEY` in the environment variables to a random 64-character hex string.
   - Do not use defaults in `.env.example`.
3. **Configure Prediction Auth Mode**:
   - In private clinical settings, set `PREDICTION_AUTH_MODE=authenticated` in `.env` to require login for inference APIs.
4. **Bcrypt Strength**: Ensure `BCRYPT_ROUNDS` is set to `12` or higher to protect user passwords against offline cracking attempts.
5. **Restrict CORS**: Configure `ALLOWED_ORIGINS` to contain only trusted frontend domains.
6. **Deploy Logs Externally**: Ship the audit logs to a secure centralized logging facility (e.g., ELK stack, Splunk) for tamper-evident retention.
