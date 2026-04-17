# CinePhix Backend

FastAPI backend for CinePhix SaaS — authentication, watchlist, favorites, and TMDB integration.

## Stack

- **FastAPI** (Python 3.11+)
- **PostgreSQL 16** + SQLAlchemy 2.0 (async)
- **Redis** (caching, sessions)
- **JWT** (Argon2id for password hashing)
- **Docker** + Docker Compose

## Features (Phase 1)

- [x] Email + password authentication
- [x] JWT access + refresh tokens
- [x] Google OAuth
- [x] Magic links (passwordless login)
- [x] User profiles with preferences
- [x] Watchlist (CRUD, reordering)
- [x] Favorites (CRUD)
- [x] TMDB proxy with Redis cache

## Quick Start

### 1. Clone and setup

```bash
git clone https://github.com/avaazquezz/CinePhix-Backend.git
cd CinePhix-Backend
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your values
```

### 3. Run with Docker

```bash
docker compose up -d
```

### 4. Run locally (development)

```bash
pip install -e ".[dev]"
uvicorn app:app --reload --port 8000
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `REDIS_URL` | Redis connection string | Yes |
| `JWT_SECRET_KEY` | Secret for signing JWTs (generate with `python -c "import secrets; print(secrets.token_hex(32))"`) | Yes |
| `TMDB_API_KEY` | API key from The Movie Database | Yes |
| `RESEND_API_KEY` | API key from Resend (email) | No |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | No |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret | No |

## Project Structure

```
cinephix-backend/
├── app/
│   ├── main.py          # FastAPI app entry point
│   ├── config.py        # Environment configuration
│   ├── database.py      # PostgreSQL async connection
│   ├── redis.py         # Redis client
│   ├── dependencies.py # Auth dependencies
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   ├── routers/         # API routes
│   ├── services/        # Business logic
│   └── utils/           # Security, caching utilities
├── migrations/          # Alembic migrations
├── tests/               # Unit + Integration tests
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

## Development

### Running Tests

```bash
pytest
```

### Code Quality

```bash
ruff check .        # Linting
mypy app/           # Type checking
```

## License

MIT