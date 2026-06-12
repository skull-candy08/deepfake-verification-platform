# Security Policy

## Supported Versions

Currently, only the `main` branch of the Deepfake Verification Platform receives security updates.

| Version | Supported          |
| ------- | ------------------ |
| v1.0.x  | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability within this project, please DO NOT create a public issue. 
Instead, please send an email to the repository maintainers. 

We will respond within 48 hours to confirm receipt and begin assessing the vulnerability.

## Automated Security Checks

This repository is protected by several automated security layers:
1. **GitHub Secret Scanning:** Automatically revokes and flags known compromised credentials.
2. **Pre-commit Hooks:** Developers must use `pre-commit install` locally. This utilizes `detect-secrets` and custom hooks to prevent `.db`, `.pdf`, and `.env` files from being committed.
3. **CI/CD Security Actions:** Every PR triggers a workflow that runs `TruffleHog` (advanced secret scanning), `Bandit` (Python SAST), and `pip-audit` to detect CVEs in the dependencies.

## Production Configuration Rules

The application uses strict validation in `production` mode:
- Rate limiting **must** use a shared `REDIS_URL`.
- Databases **cannot** be local SQLite files.
- `FLASK_SECRET_KEY` and `JWT_SECRET_KEY` **must** be strong, unique 32+ character strings.

Do not attempt to bypass these validations.
