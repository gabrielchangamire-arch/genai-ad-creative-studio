# GenAI Ad Creative Studio

GenAI Ad Creative Studio is a full-stack campaign workspace for drafting advertising copy from a product brief. It keeps campaign inputs and creative sets together so the copy workflow can be tested locally before a provider integration is enabled.

## Features

- Create campaign briefs with product details, audience, tone, and objective.
- Store campaigns in SQLite for local development.
- Browse saved campaigns and reopen a creative set.
- Generate headlines, descriptions, calls to action, and campaign concepts.
- Run in mock generation mode without a provider key.
- Validate the backend workflow with pytest.

## Tech Stack

- Backend: Python, FastAPI, SQLite
- Frontend: React, Vite
- Testing: pytest, FastAPI TestClient
- Automation: GitHub Actions

## Architecture

The FastAPI backend owns campaign storage and generation orchestration. Campaigns are persisted in a local SQLite database through a small repository layer, while the generation service selects mock mode or a provider-backed mode from environment configuration.

The React client calls the campaign API and keeps the first screen focused on the workflow:

1. Capture a campaign brief.
2. Save the campaign.
3. Generate and review a creative set.
4. Reopen prior campaigns from the workspace list.

## Setup

### Backend

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements-dev.txt
uvicorn app.main:app --app-dir backend --reload
```

The backend listens on `http://localhost:8000`.

### Frontend

Open a second terminal from the repository root:

```powershell
cd frontend
npm install
npm run dev
```

The Vite dev server listens on `http://localhost:5173` and proxies API calls to the backend during local development.

## Tests

Run backend tests from the repository root:

```powershell
cd backend
pytest
```

Build the frontend production bundle:

```powershell
cd frontend
npm run build
```

## Environment Variables

| Variable | Purpose | Default |
| --- | --- | --- |
| `DATABASE_URL` | SQLite database location for campaign storage. | `backend/data/studio.db` |
| `GENERATION_MODE` | Generation mode. Use `mock` locally or `provider` for a configured provider endpoint. | `mock` |
| `GENAI_PROVIDER_API_KEY` | API key sent to the configured provider endpoint. | Empty |
| `GENAI_PROVIDER_BASE_URL` | Provider endpoint that returns structured copy data. | Empty |
| `GENAI_PROVIDER_MODEL` | Model identifier passed to the provider endpoint. | Empty |
| `FRONTEND_ORIGINS` | Comma-separated origins allowed by backend CORS. | `http://localhost:5173` |
| `VITE_API_BASE_URL` | Optional frontend API origin for non-proxied deployments. | Empty |

Start with `.env.example`, keep the real `.env` file local, and leave `GENERATION_MODE=mock` until provider settings are ready.

## Future Improvements

- Add campaign revisions and side-by-side creative comparisons.
- Support PostgreSQL for deployed environments.
- Add provider-specific adapters with retry and usage tracking.
- Add export flows for review docs and ad platform templates.
