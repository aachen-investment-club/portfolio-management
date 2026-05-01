#!/bin/bash
set -e

# ========== Configurable parameters ==========
# Usage: ./deploy.sh [container_name] [host_port] [container_port] [db_alias]
CONTAINER_NAME="${1:-portfolio-app}"
HOST_PORT="${2:-80}"
CONTAINER_PORT="${3:-5000}"
DB_HOST_ALIAS="${4:-db-host}"

# ========== AWS Configuration ==========
# Set via environment variables or use defaults
ECR_REPO_URI="${ECR_REPO_URI:-<your-account-id>.dkr.ecr.<region>.amazonaws.com/<your-repo-name>}"
REGION="${AWS_REGION:-eu-central-1}"

# Validate ECR_REPO_URI is set
if [[ "$ECR_REPO_URI" == *"<your-account-id>"* ]]; then
    echo "Error: ECR_REPO_URI must be set via environment variable"
    echo "Usage: ECR_REPO_URI=123456789.dkr.ecr.eu-central-1.amazonaws.com/my-repo ./deploy.sh"
    exit 1
fi

# Get EC2 private IP from instance metadata
EC2_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)

# Ensure database directory exists on EC2 host
DB_HOST_DIR="/data"
mkdir -p "$DB_HOST_DIR"

# Authenticate Docker to ECR
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_REPO_URI

# Pull the latest image
docker pull $ECR_REPO_URI:latest

# Stop & remove existing container (if any)
docker stop $CONTAINER_NAME || true
docker rm $CONTAINER_NAME || true

# Run new container with host-database connection
# Database is stored on EC2 host at /data/market.db (persists across container restarts)
docker run -d \
  --name $CONTAINER_NAME \
  --add-host=$DB_HOST_ALIAS:$EC2_IP \
  -e DB_HOST=$DB_HOST_ALIAS \
  -e DB_PATH="sqlite:////data/market.db" \
  -v $DB_HOST_DIR:/data \
  -p $HOST_PORT:$CONTAINER_PORT \
  $ECR_REPO_URI:latest

echo "Deployment complete. Container $CONTAINER_NAME is running on port $HOST_PORT"
echo "Database persisted on EC2 host at $DB_HOST_DIR/market.db"
