#!/bin/bash
set -e

# ========== Configurable parameters ==========
# Usage: ./deploy.sh [container_name] [host_port] [container_port] [db_alias]
# Note: When run via CodeDeploy appspec.yml, these are passed as environment variables
CONTAINER_NAME="${CONTAINER_NAME:-portfolio-app}"
HOST_PORT="${HOST_PORT:-80}"
CONTAINER_PORT="${CONTAINER_PORT:-5000}"
DB_HOST_ALIAS="${DB_HOST_ALIAS:-db-host}"

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

# Get EC2 private IP from instance metadata (supports both IMDSv1 and IMDSv2)
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" 2>/dev/null || true)
if [ -n "$TOKEN" ]; then
  EC2_IP=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/local-ipv4)
else
  EC2_IP=$(curl -s http://169.254.169.254/latest/meta-data/local-ipv4)
fi

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

# Determine .env file location
# Priority: 1) /home/ec2-user/portfolio-management/.env (production), 2) ./.env (local testing)
ENV_FILE=""
if [ -f "/home/ec2-user/portfolio-management/.env" ]; then
  ENV_FILE="/home/ec2-user/portfolio-management/.env"
elif [ -f ".env" ]; then
  ENV_FILE=".env"
fi

# Require .env file to be present
if [ -z "$ENV_FILE" ]; then
  echo "ERROR: .env file not found."
  echo "Please create /home/ec2-user/portfolio-management/.env with required environment variables."
  echo "See docs/ci_cd_pipeline_setup.md for the list of required variables."
  exit 1
fi

echo "Using environment file: $ENV_FILE"

# Validate that DB_PATH is defined in .env (critical for persistent database)
if ! grep -q '^DB_PATH=' "$ENV_FILE"; then
  echo "ERROR: $ENV_FILE must contain DB_PATH setting (e.g., DB_PATH=sqlite:////data/market.db)"
  exit 1
fi

# Build docker run options
DOCKER_RUN_OPTS="--env-file $ENV_FILE"

# Run new container with host-database connection
# Database is stored on EC2 host at /data/market.db (persists across container restarts)
docker run -d \
  --name $CONTAINER_NAME \
  --add-host=$DB_HOST_ALIAS:$EC2_IP \
  -e DB_HOST=$DB_HOST_ALIAS \
  $DOCKER_RUN_OPTS \
  -v $DB_HOST_DIR:/data \
  -p $HOST_PORT:$CONTAINER_PORT \
  $ECR_REPO_URI:latest

echo "Deployment complete. Container $CONTAINER_NAME is running on port $HOST_PORT"
echo "Database persisted on EC2 host at $DB_HOST_DIR/market.db"
