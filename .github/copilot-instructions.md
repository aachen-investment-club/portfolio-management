# Guidance for AI coding agents working on this repository

This file contains short, actionable information an AI agent needs to be productive in this codebase.

Project at-a-glance
- A Flask webapp that serves a portfolio-management dashboard. Entrypoint: `wsgi.py` which builds the `Flask` app from `portfolio.__main__` and registers blueprints.
- Two main blueprints: `portfolio/routes.py` (frontend routes, templates) and `portfolio/backend.py` (API endpoints under `bp_api`).
- Data persistence: lightweight local SQLite DB at `market.db` (SQLAlchemy engine configured in `portfolio/utils/aws_config.py`). Some code contains commented Athena configuration — the app expects SQLite by default.
- Static frontend in `templates/` and `static/` (JS/CSS). Template rendering happens in `routes.index()`.

Key files and directories
- `wsgi.py` — application creation, Sentry init, DB metadata create, and CLI-run behavior when executed directly.
- `portfolio/__main__.py` — module used by `python -m portfolio` (application runner). The `app` object is provided here.
- `portfolio/routes.py` — main site routes (login, index, upload/remove portfolio, health, update_market). Shows caching and session usage.
- `portfolio/backend.py` — JSON API endpoints used by the frontend (`/api/...`).
- `portfolio/extensions.py` — Flask extensions initialised (cache, oauth). Use these instead of creating new extension instances.
- `portfolio/models/` — domain models: `Market`, `Portfolio`, `Metrics`, `Alpaca` wrapper. Tests exercise `Market` (see `test/test_market.py`).
- `portfolio/utils/aws_config.py` — shows how database engine is created. Default is `sqlite:///market.db`.

Conventions & patterns to follow (project-specific)
- Single Flask app: register blueprints in `wsgi.py`. Avoid creating extra Flask apps.
- App uses `flask_caching.Cache` via `cache.memoize` for heavy computations. Use `cache.memoize(timeout=...)` for functions that return deterministic results (see `get_cached_nav_data` in `routes.py`).
- Authorization uses Authlib `OAuth` and stores user in `session['user']`. Routes that require login use decorator `check_auth` in `routes.py`.
- DB migrations are not present — code creates tables at startup (`Base.metadata.create_all(engine)` in `wsgi.py`). When changing models, add a note in PRs to update DB manually or add migration steps.
- Market data is loaded from CSV in `data/` during first run (see `wsgi.py` guarded code). The `data/` files are large and intentionally excluded from Docker build by `.dockerignore`.

Dev & test workflows (commands discovered in repo)
- Run app locally (development):
  - Create `.env` from `.env.example` and set secrets.
  - Option A (module runner): `python3.12 -m portfolio` (this runs Flask's built-in server and will load market CSVs if DB empty).
  - Option B (wsgi/gunicorn): `gunicorn --bind 127.0.0.1:5000 wsgi:app --workers 2`
- Run tests: `python -m unittest discover -s test` (tests expect environment variables e.g. Alpaca keys for some tests). See `test/test_market.py` for requirements.
- Build docs (Sphinx): run in `docs/` -> `sphinx-build -b html . _build`.

Docker / container notes (added files)
- A `Dockerfile` and `docker-compose.yml` are included. Important points:
  - Image uses Python 3.12-slim and installs `requirements.txt`.
  - Entrypoint runs `gunicorn wsgi:app` binding to 0.0.0.0:5000.
  - `docker-compose.yml` mounts `market.db` and `data/` from host to container so large CSV and DB don't need to be baked into the image.

Example Docker workflow (explicit commands to use):
```bash
# build image
docker build -t aic/portfolio-management:local .

# run with docker (exposes 5000)
docker run --rm -p 5000:5000 \
  -v "${PWD}/market.db:/app/market.db" \
  -v "${PWD}/data:/app/data:ro" \
  --env-file .env \
  aic/portfolio-management:local

# or with docker-compose
docker compose up --build
```

Environment hints
- The app reads many environment variables. Minimums commonly required for local run: `FLASK_SECRET_KEY`, database-related vars are optional (defaults to SQLite). For auth features you’ll need Cognito vars (`COGNITO_*`, `COGNITO_CLIENT_ID`, `AWS_COGNI_CLIENT_SECRET`) — these can be stubbed for local dev if you skip auth routes.

Testing and quick smoke checks
- Health endpoint: `GET /health` (see `routes.health`). Use this for a quick container smoke test.
- If DB is empty the app's startup path in `wsgi.py` will import CSVs; ensure the `data/` mount is present or pre-populate `market.db` locally and mount it.

What an AI agent should do on PRs
- When editing models or DB schema, add migration instructions or update `wsgi.py` startup behavior; flag that DB changes need manual handling since Alembic is not configured.
- When adding new endpoints, register blueprints in `wsgi.py` and use existing `cache`, `oauth` instances from `portfolio/extensions.py`.
- Reuse the `engine` from `portfolio/utils/aws_config.py` — don’t create a second engine; tests and `wsgi.py` rely on the same `market.db` path.

Examples to cite in changes
- Caching pattern: `@cache.memoize(timeout=600)` on `get_cached_nav_data` in `portfolio/routes.py`.
- Blueprint registration: `app.register_blueprint(bp)` and `app.register_blueprint(bp_api)` in `wsgi.py`.
- DB engine creation: `engine = create_engine("sqlite:///market.db", echo=False)` in `portfolio/utils/aws_config.py`.

If something is missing
- If `.env.example` or required credentials are not present, ask the repository owners for guidance (market data and Alpaca credentials are protected).

If you want me to iterate on these instructions or add CI-specific guidance (e.g., GitHub Actions for build/test), tell me which CI provider the project will use.
