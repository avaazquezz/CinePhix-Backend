# PR: Phase 1 - Foundation

## Branch: `feature/phase1-foundation`

## Description

Phase 1 implementation of CinePhix SaaS backend. Complete foundation including:

### Authentication
- Email + password registration and login
- JWT access tokens (15min) + refresh tokens (7 days)
- Google OAuth integration
- Magic links for passwordless login
- Argon2id password hashing (secure)

### User Management
- User profiles with display name, avatar
- User preferences (genres, decade, min_rating, language)
- JSONB storage for flexible preferences

### Watchlist & Favorites
- Full CRUD for watchlist items (reorderable)
- Full CRUD for favorites
- Unique constraint per user+tmdb_id+media_type

### TMDB Integration
- Proxy endpoints with Redis caching
- Trending (15min cache), Movie details (1h cache), Search (5min cache)
- Rate limiting ready

### Infrastructure
- Docker + Docker Compose (PostgreSQL 16, Redis 7, API)
- Alembic migrations
- Health check endpoint
- Validation script

## Files Changed

```
app/
├── main.py, config.py, database.py, redis.py, dependencies.py
├── models/ (user.py, watchlist.py, favorite.py, enums.py)
├── schemas/ (auth.py, user.py, watchlist.py, favorite.py, media.py)
├── routers/ (auth.py, users.py, watchlist.py, favorites.py, tmdb.py)
├── services/ (auth_service.py, tmdb_service.py, email_service.py)
└── utils/ (security.py, cache.py)
migrations/ (env.py, versions/001_initial.py)
tests/ (unit/test_auth.py, integration/test_api.py, conftest.py)
Dockerfile, docker-compose.yml, pyproject.toml, validate.sh
```

## To Create PR

```bash
cd cinephix-backend
git checkout -b feature/phase1-foundation  # already on this branch
git push -u origin feature/phase1-foundation

# Then create PR via GitHub UI or:
gh pr create --base main --head feature/phase1-foundation --title "Phase 1: Foundation" --body "$(cat PULL_REQUEST_TEMPLATE.md)"
```

## Review Checklist

- [ ] All Python files compile without syntax errors
- [ ] Migrations create correct PostgreSQL schema
- [ ] Auth endpoints return proper JWT tokens
- [ ] Protected endpoints return 403 without auth
- [ ] Docker compose builds and starts successfully
- [ ] Validation script passes all checks
- [ ] No hardcoded secrets (all in .env)

## Next Steps (Phase 2)

Once merged to main:
1. Frontend Pinia stores (auth, user, watchlist, favorites)
2. Router guards for protected routes
3. Login/Register UI components
4. Watchlist sync with backend API
5. Cypress E2E tests