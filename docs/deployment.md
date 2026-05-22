# Deployment

## Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

Services:

- Backend: http://localhost:8001
- API docs: http://localhost:8001/docs
- Frontend: http://localhost:3000

SQLite runtime data is stored in the Docker named volume `research-radar-hub_backend-data`. Cache files and generated reports are mounted into local `cache/` and `reports/` folders.

## Local Backend

```powershell
python -m venv backend/venv
backend\venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
pytest tests -q
uvicorn backend.main:app --reload --port 8000
```

## Local Frontend

```powershell
cd frontend
npm install
npm run dev
```

Set `NEXT_PUBLIC_API_PROXY_BASE=http://localhost:8000` when running the frontend outside Docker.

## Daily Email On Windows

Create a Windows Task Scheduler task that runs:

```powershell
cd E:\xuexi\open-data-hub
backend\venv\Scripts\python.exe -m backend.scripts.research_radar --collect --send
```

Configure SMTP values in `.env` before using `--send`.

## Optional Secrets

- `GITHUB_PAT`: raises GitHub public API limits.
- `OPENAI_API_KEY`: enables LLM summaries.
- `OPENAI_BASE_URL` and `OPENAI_MODEL`: use an OpenAI-compatible provider such as SiliconFlow.
- SMTP settings: enable email delivery.
