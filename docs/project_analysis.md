# Portfolio Management - Project Analysis

## 1. Project Purpose

### Overview
A **portable, lightweight dashboard** with custom metrics to visualize portfolios managed by a portfolio management group. It provides:

- **Portfolio visualization**: Interactive web dashboard showing portfolio performance over time
- **Performance metrics**: ROI, CAGR, volatility, Sharpe ratio, maximum drawdown, beta, alpha
- **Benchmark comparison**: Compares portfolio performance against US Treasury bonds
- **Portfolio management**: Upload, remove, and compare multiple portfolios
- **Purchase simulation**: Simulate trades and see projected performance
- **Authentication**: AWS Cognito OIDC-based login

### Target Users
- AIC Developer members (portfolio management group)
- Portfolio managers who need to track and compare portfolio performance

---

## 2. Architecture & Infrastructure

### Tech Stack
| Layer | Technology |
|-------|------------|
| **Backend** | Python 3.12, Flask |
| **Database** | SQLite (local file: `market.db`) |
| **ORM** | SQLAlchemy |
| **Frontend** | HTML templates, JavaScript, Plotly (implied) |
| **Containerization** | Docker (multi-stage build) |
| **CI/CD** | AWS CodePipeline, CodeBuild, CodeDeploy |
| **Container Registry** | AWS ECR |
| **Authentication** | AWS Cognito (OIDC) |
| **Error Monitoring** | Sentry SDK |
| **Caching** | Flask-Caching (SimpleCache) |
| **Market Data** | yfinance, Alpaca API |
| **Portfolio Storage** | AWS S3 (`portfolio-management-developer` bucket) |

### Infrastructure Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        AWS Cloud                            │
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐ │
│  │  CodePipeline│───▶│  CodeBuild  │───▶│   CodeDeploy    │ │
│  │             │    │ (Docker     │    │ (EC2 deploy)    │ │
│  └─────────────┘    │  build)     │    └────────┬────────┘ │
│                     └──────┬──────┘             │          │
│                            │                    │          │
│                            ▼                    ▼          │
│                     ┌─────────────┐    ┌─────────────────┐ │
│                     │     ECR     │    │     EC2         │ │
│                     │ (Container  │    │  ┌───────────┐  │ │
│                     │  Registry)  │    │  │  Docker   │  │ │
│                     └─────────────┘    │  │ Container │  │ │
│                                        │  │ (Flask)   │  │ │
│                                        │  └───────────┘  │ │
│                                        │  ┌───────────┐  │ │
│                                        │  │ SQLite DB │  │ │
│                                        │  │(market.db)│  │ │
│                                        │  └───────────┘  │ │
│                                        └─────────────────┘ │
│                                                             │
│  ┌─────────────┐    ┌─────────────┐                        │
│  │   Cognito   │    │     S3      │                        │
│  │  (Auth)     │    │(Portfolios) │                        │
│  └─────────────┘    └─────────────┘                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    External Services                        │
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐ │
│  │  yfinance   │    │  Alpaca API │    │ US Treasury API │ │
│  │(Market Data)│    │(Trading/Cal)│    │  (Bonds Data)   │ │
│  └─────────────┘    └─────────────┘    └─────────────────┘ │
│                                                             │
│  ┌─────────────┐                                            │
│  │   Sentry    │                                            │
│  │(Monitoring) │                                            │
│  └─────────────┘                                            │
└─────────────────────────────────────────────────────────────┘
```

### Deployment Flow
1. **CodePipeline** triggers on repo changes
2. **CodeBuild** builds Docker image and pushes to ECR
3. **CodeDeploy** pulls image on EC2 and runs container
4. **SQLite database** persists on EC2 host (not in container)
5. **Cronjob** (systemd timer) updates market data weekdays at 09:00

---

## 3. Project Structure

```
portfolio-management/
├── .env.example              # Environment variable template
├── .gitignore                # Git ignore rules
├── .dockerignore             # Docker ignore rules
├── Dockerfile                # Multi-stage Docker build (test + production)
├── docker-compose.yml        # Local Docker Compose configuration
├── requirements.txt          # Python dependencies
├── wsgi.py                   # WSGI entry point (imports app from portfolio)
│
├── buildspec.yml             # AWS CodeBuild configuration
├── appspec.yml               # AWS CodeDeploy configuration
│
├── portfolio/                # Main application package
│   ├── __init__.py
│   ├── __main__.py           # App initialization, Cognito config, Flask setup
│   ├── market_updater.py     # Standalone market update script
│   ├── backend.py            # API blueprint (simulation, portfolio data)
│   ├── routes.py             # Web blueprint (pages, auth, uploads)
│   ├── exceptions.py         # Custom exception classes
│   ├── extensions.py         # Flask extensions (cache, oauth)
│   │
│   ├── models/               # Business logic layer
│   │   ├── __init__.py
│   │   ├── market.py         # Market data: load, query, update prices
│   │   ├── portfolio.py      # Portfolio: NAV, positions, trades, S3 storage
│   │   ├── metrics.py        # Financial metrics: Sharpe, Beta, Alpha, etc.
│   │   ├── alpaca_wrapper.py # Alpaca trading API wrapper
│   │   └── mock_file.py      # Mock data for testing
│   │
│   ├── schemas/              # Database models (SQLAlchemy)
│   │   └── market.py         # MarketDB, TickerMeta tables
│   │
│   ├── utils/                # Utility functions
│   │   ├── aws_config.py     # SQLAlchemy engine, DB path config
│   │   ├── portfolio_builder.py  # Portfolio construction helpers
│   │   ├── simulate.py       # Purchase simulation logic
│   │   └── validators.py     # Input validation
│   │
│   ├── static/               # Static assets
│   │   └── index.css         # Dashboard styles
│   │
│   └── templates/            # Jinja2 templates
│       ├── index.html        # Main dashboard page
│       ├── index.js          # Dashboard JavaScript
│       └── components/       # Reusable template components
│           ├── metrics.html
│           ├── positions.html
│           ├── simulation.html
│           ├── purchase_simulation.html
│           └── plot_control_panel.html
│
├── scripts/                  # Deployment scripts
│   ├── deploy.sh             # Production deployment script
│   ├── test_local_appspec.sh # Local appspec testing
│   └── DEPLOY_INSTRUCTIONS.md
│
├── test/                     # Unit tests
│   ├── __init__.py
│   ├── test_market.py        # Market model tests
│   └── test_metrics.py       # Metrics calculation tests
│
├── docs/                     # Documentation
│   ├── project_analysis.md   # This file
│   ├── ci_cd_notes.md        # CI/CD setup notes
│   ├── cronjob_setting.md    # Systemd timer configuration
│   ├── service               # Service file template
│   └── (Sphinx docs)
│
└── data/                     # Market data CSVs (gitignored)
    ├── sp500_close_extended.csv
    ├── sp500_close_current.csv
    └── ticker_metadata.csv
```

### Directory Responsibilities
| Directory | Purpose |
|-----------|---------|
| `portfolio/` | All application code - models, routes, templates, utilities |
| `portfolio/models/` | Core business logic - market data, portfolios, metrics |
| `portfolio/schemas/` | Database ORM models |
| `portfolio/utils/` | Shared utilities and configuration |
| `scripts/` | Deployment and operational scripts |
| `test/` | Unit tests for models and metrics |
| `docs/` | Project documentation and operational guides |
| `data/` | Input CSV files for market data (not committed to git) |

---

## 4. Application Context

### Key Components

#### Models
| File | Purpose |
|------|---------|
| [`portfolio/models/market.py`](portfolio/models/market.py:1) | Market data management - loading, querying, updating stock prices |
| [`portfolio/models/portfolio.py`](portfolio/models/portfolio.py:1) | Portfolio logic - NAV calculation, positions, trades, S3 storage |
| [`portfolio/models/metrics.py`](portfolio/models/metrics.py:1) | Financial metrics - Sharpe, Beta, Alpha, CAGR, drawdown, etc. |
| [`portfolio/models/alpaca_wrapper.py`](portfolio/models/alpaca_wrapper.py:1) | Alpaca trading API wrapper |

#### Routes
| Blueprint | File | Purpose |
|-----------|------|---------|
| `bp` | [`portfolio/routes.py`](portfolio/routes.py:1) | Main web routes (index, auth, portfolio upload/remove) |
| `bp_api` | [`portfolio/backend.py`](portfolio/backend.py:1) | API endpoints (simulate purchase, portfolio data) |

#### Database Schema
| Table | File | Columns |
|-------|------|---------|
| `portfolio_management_developer` | [`portfolio/schemas/market.py`](portfolio/schemas/market.py:10) | ticker, date, price_close |
| `ticker_metadata` | [`portfolio/schemas/market.py`](portfolio/schemas/market.py:20) | ticker, exchange, shortname, longname, sector, industry, origin, type, currency |

### Data Flow
```
CSV Data (./data/) ──▶ Market.load_from_csv() ──▶ SQLite (market.db)
                                                        │
yfinance/Alpaca ──▶ Market.update_market() ────────────▶│
                                                        ▼
S3 Portfolios ──▶ Portfolio.import_from_dict() ──▶ NAV Calculation
                                                        │
                                                        ▼
Metrics.get_*() ──▶ Dashboard Rendering ◀───────── US Treasury Bonds
```

---

## 5. Troubleshooting & Issues Found

### 4.1 Issues Fixed ✅

#### A. requirements.txt Encoding Problem - FIXED
**File:** [`requirements.txt`](requirements.txt:1)

Converted from UTF-16 to UTF-8 encoding. The file was originally encoded in UTF-16 (little-endian with BOM), which caused pip to fail when parsing dependencies.

#### B. Port Mismatch in appspec.yml - FIXED
**File:** [`appspec.yml`](appspec.yml:14)

`CONTAINER_PORT` was already updated to `"5000"` to match the Dockerfile's exposed port and gunicorn binding.

#### C. Missing pytest in requirements - FIXED
**File:** [`requirements.txt`](requirements.txt:117)

Added `pytest` to requirements.txt. The Dockerfile runs tests during the build stage, but pytest was not listed as a dependency.

#### D. Missing Static Files in Docker - FIXED
**File:** [`Dockerfile`](Dockerfile:37-39)

Added COPY commands for static files (CSS) and templates (HTML/JS). These were previously commented out, causing the production container to serve pages without styling.

#### E. Market Update Endpoint Auth - FIXED
**File:** [`portfolio/routes.py`](portfolio/routes.py:133)

Added `@check_auth` decorator to `/update_market` endpoint. Previously, anyone could trigger expensive market data fetches from Alpaca/yfinance without authentication.

#### F. Hardcoded Cognito Configuration - FIXED
**File:** [`portfolio/__main__.py`](portfolio/__main__.py:37-38)

Moved Cognito user pool ID and AWS region to environment variables (`COGNITO_USER_POOL_ID`, `AWS_REGION`) with sensible defaults. This allows easy switching between environments (dev/staging/prod) without code changes.

#### G. Duplicate load_dotenv() Calls - FIXED
**File:** [`portfolio/__main__.py`](portfolio/__main__.py:5)

Removed redundant second `load_dotenv()` call that was executed after imports.

#### H. requirements.txt.orig File - FIXED
**File:** `.gitignore`

Added `*.orig` pattern to `.gitignore` and deleted the backup file to keep the repository clean.

#### I. Database Persistence on EC2 Host - FIXED
**Files:** [`portfolio/utils/aws_config.py`](portfolio/utils/aws_config.py:16), [`scripts/deploy.sh`](scripts/deploy.sh:29)

Made database path configurable via `DB_PATH` environment variable. The deploy script now:
- Creates a `/data` directory on the EC2 host
- Mounts this directory into the container via Docker volume
- Sets `DB_PATH` to point to the host-mounted path (`sqlite:////data/market.db`)

This ensures the SQLite database persists on the EC2 host filesystem and survives container restarts and redeployments, addressing the CI/CD note: "DB should be in EC2; not docker (to avoid wipe outs)".

#### J. deploy.sh Configuration via Environment Variables - FIXED
**File:** [`scripts/deploy.sh`](scripts/deploy.sh:12)

Refactored the deploy script to accept AWS configuration via environment variables instead of requiring manual editing of placeholder values:
- `ECR_REPO_URI` - Set via environment variable (script validates and exits with helpful error if not set)
- `REGION` - Uses standard `AWS_REGION` environment variable with default fallback

The script now also has sensible defaults for container name (`portfolio-app`), host port (`80`), and container port (`5000`).

**Usage:** `ECR_REPO_URI=123456789.dkr.ecr.eu-central-1.amazonaws.com/my-repo ./deploy.sh`

### 4.2 Remaining Issues

No critical issues remain. The deployment script is now fully configurable via environment variables without requiring code changes.

---

## 6. Recommendations

### Immediate Actions
1. **Fix requirements.txt encoding** - Convert from UTF-16 to UTF-8
2. **Fix port mismatch** - Update `CONTAINER_PORT` to `5000` in appspec.yml
3. **Add pytest to requirements.txt** - Required for Docker build
4. **Configure deploy.sh** - Replace placeholder ECR and REGION values
5. **Uncomment static files copy** in Dockerfile

### Security Improvements
1. **Add authentication** to `/update_market` endpoint
2. **Move Cognito config** to environment variables
3. **Review S3 bucket permissions** for `portfolio-management-developer`
4. **Rotate credentials** in `.env.example` template

### Infrastructure Improvements
1. **Consider migrating SQLite to RDS** for better durability and multi-instance support
2. **Add health check** to Dockerfile for ECS/EKS compatibility
3. **Implement proper secrets management** (AWS Secrets Manager instead of .env)
4. **Add CloudWatch logging** integration

### Code Quality
1. **Remove `requirements.txt.orig`** or add to `.gitignore`
2. **Remove duplicate `load_dotenv()`** calls
3. **Add type hints** consistently across the codebase
4. **Add unit tests** for Portfolio and Metrics classes
5. **Consider using Alembic** for database migrations

---

## 7. Environment Variables Required

| Variable | Purpose | Example |
|----------|---------|---------|
| `FLASK_SECRET_KEY` | Flask session encryption | `your-secret-key` |
| `COGNITO_CLIENT_ID` | AWS Cognito app client ID | `abc123...` |
| `COGNITO_DOMAIN_PREFIX` | Cognito domain prefix | `your-domain` |
| `AWS_COGNI_CLIENT_SECRET` | Cognito client secret | `secret...` |
| `AWS_REGION` | AWS region | `eu-central-1` |
| `AWS_ACCESS_KEY_ID` | AWS access key | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | `secret...` |
| `SENTRY_DSN` | Sentry error tracking DSN | `https://...` |
| `API_ROUTE` | API base URL | `http://localhost:5000` |
| `APCA_API_KEY_ID` | Alpaca API key (for market updates) | `key...` |
| `APCA_API_SECRET_KEY` | Alpaca secret key | `secret...` |

---

## 8. Quick Start Commands

```bash
# Local development
python3.12 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python -m portfolio

# Docker build and run
docker-compose up --build

# Update market manually
python market_updater.py

# Build documentation
cd docs/ && sphinx-build -b html . _build
```

---

*Analysis generated on 2026-05-01*
