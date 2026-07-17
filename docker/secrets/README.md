# Docker Secrets

This directory holds Docker Compose secret files for production deployments.

**These files are git-ignored and must be created manually on each deployment host.**

## Required Files

| File | Description | Minimum Length |
|---|---|---|
| `jwt_secret_key.txt` | JWT signing secret | 64 characters |
| `db_encryption_key.txt` | Database encryption key | 32 characters |

## Generating Secrets

```bash
# JWT secret (64-char hex)
python -c "import secrets; print(secrets.token_hex(32))" > jwt_secret_key.txt

# DB encryption key (32-char hex)
python -c "import secrets; print(secrets.token_hex(16))" > db_encryption_key.txt
```

Or on Windows PowerShell:

```powershell
# JWT secret
python -c "import secrets; print(secrets.token_hex(32))" | Set-Content jwt_secret_key.txt

# DB key
python -c "import secrets; print(secrets.token_hex(16))" | Set-Content db_encryption_key.txt
```

## Security Notes

- Never commit these files to git (they are in `.gitignore`)
- Rotate secrets periodically
- Use a proper secrets manager (Vault, AWS Secrets Manager) in production
