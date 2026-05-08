#!/bin/bash
# create-codedeploy-app.sh
# Creates the CodeDeploy application

set -e

# Load environment variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/cicd.env"

echo "=== Creating CodeDeploy Application ==="

# Create the CodeDeploy application
echo "Creating CodeDeploy application: ${CODEDEPLOY_APP_NAME}..."

aws deploy create-application \
  --application-name "${CODEDEPLOY_APP_NAME}" \
  --compute-platform EC2 \
  --region "${AWS_REGION}" 2>/dev/null || echo "CodeDeploy application already exists"

echo "=== CodeDeploy Application Created ==="
echo "Application Name: ${CODEDEPLOY_APP_NAME}"