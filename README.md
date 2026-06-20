# TrustLens Backend

FastAPI backend service for TrustLens. It exposes the REST API used by the frontend for authentication, classes, assignments, submissions, jobs, reports, and exports.

## Tech Stack

- Python 3.11+
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- Uvicorn

## Project Structure

```text
app/
  api/v1/        API routers and endpoints
  core/          Application settings
  db/            Database session and initialization
  models/        SQLAlchemy models
  schemas/       Pydantic schemas
  services/      Business logic
  processing/    Document analysis helpers
  export/        Report export utilities
alembic/         Database migrations
```

## Setup

```powershell
cd apps/backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create a `.env` file:

```env
PROJECT_NAME=TrustLens API
API_V1_PREFIX=/api/v1
DATABASE_URL=postgresql+psycopg://postgres:your_password@localhost:5432/trustlens_db
SECRET_KEY=change-this-secret
CORS_ORIGINS=http://localhost:5173
```

## Database

Run Alembic migrations after the database exists:

```powershell
alembic upgrade head
```

## Development

```powershell
uvicorn app.main:app --reload
```

Default URLs:

- API root: `http://localhost:8000`
- Swagger docs: `http://localhost:8000/docs`
- API v1: `http://localhost:8000/api/v1`

## Useful Commands

```powershell
# Create a migration after model changes
alembic revision --autogenerate -m "describe change"

# Apply migrations
alembic upgrade head
```
