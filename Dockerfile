# ---- Stage 1: test the code ----
FROM python:3.12-slim AS tester

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Install system dependencies (needed for some Python packages)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc git curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first (for Docker layer caching)
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the entire project (including portfolio/, test/, wsgi.py, etc.)
COPY . /app

# Run tests – if any fail, the build stops here
RUN pytest test/ --maxfail=1 --disable-warnings

# ---- Stage 2: final image (runtime only) ----
# Use the SAME base image as tester
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies (same as tester, but without test-only packages)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy only the application runtime files from the tester stage (exclude tests, dev files)
COPY --from=tester /app/portfolio /app/portfolio
COPY --from=tester /app/wsgi.py /app/wsgi.py

# Production settings
ENV FLASK_APP=wsgi.py
ENV FLASK_DEBUG=0

EXPOSE 5000

# Use gunicorn (already installed via requirements.txt)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "wsgi:app", "--workers", "2", "--timeout", "120"]
