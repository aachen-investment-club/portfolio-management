FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Install system dependencies required by some python packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc git curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy project
COPY . /app

ENV FLASK_APP=wsgi.py
ENV FLASK_ENV=production

EXPOSE 5000

# Use gunicorn and bind to 0.0.0.0 so containers are reachable from host
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "wsgi:app", "--workers", "2", "--timeout", "120"]
