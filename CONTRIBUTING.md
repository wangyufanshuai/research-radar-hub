# Contributing

Thanks for contributing to Research Radar Hub.

## Development Setup

```bash
python -m venv backend/venv
backend/venv/Scripts/Activate.ps1
pip install -r backend/requirements.txt
pytest tests -q
```

Frontend:

```bash
cd frontend
npm install
npm run build
```

## Guidelines

- Keep collectors polite: use official public APIs or pages, respect robots.txt, and preserve rate limits.
- Do not add code that bypasses login walls, paywalls, CAPTCHA, or access controls.
- Do not commit `.env`, SQLite databases, cache files, generated reports, or virtual environments.
- Add focused tests for new collectors, report behavior, and API routes.
- Prefer small, reviewable changes.

## Pull Requests

Include:

- What changed and why.
- How it was tested.
- Any new configuration or data-source compliance notes.
