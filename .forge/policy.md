# Autonomous Forge Policy

## Allowed paths

- `src/**`
- `tests/**`
- `docs/**`
- `README.md`
- `.ai/**`
- `.forge/**`
- `.gitignore`
- `pyproject.toml`

## Prohibited paths

- `.env`
- `.env.*`
- `**/*secret*`
- `**/*token*`
- `**/*.pem`
- `**/*.key`
- `.github/workflows/**`

## Human approval required

- Adding network access or external service calls.
- Running external commands from product code.
- Changing GitHub workflow permissions.
- Changing repository visibility, licensing, branch protection, or access controls.
- Adding telemetry, analytics, tracking, or personal-data collection.

## Validation expectations

- Run targeted tests for changed behavior.
- Run `PYTHONPATH=src python -m pytest` before committing when a checkout-capable environment is available.
- Record unavailable validation honestly in `.ai/AUTONOMOUS_STATE.md`.
