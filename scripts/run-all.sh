#!/bin/bash
# run-all.sh
# Master script to run all CI/CD setup scripts in order

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "========================================="
echo "AWS CodePipeline CI/CD Setup"
echo "========================================="
echo ""

# Load environment variables
source "${SCRIPT_DIR}/cicd.env"

# Validate required variables
REQUIRED_VARS=("AWS_REGION" "GITHUB_OWNER" "GITHUB_REPO" "GITHUB_BRANCH")
for var in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!var}" ]; then
    echo "ERROR: Required variable '${var}' is not set in cicd.env"
    exit 1
  fi
done

# Validate required secrets
source "${SCRIPT_DIR}/cicd.secrets"
REQUIRED_SECRETS=("GITHUB_OAUTH_TOKEN")
for var in "${REQUIRED_SECRETS[@]}"; do
  if [ -z "${!var}" ]; then
    echo "ERROR: Required secret variable '${var}' is not set in cicd.secrets"
    exit 1
  fi
done

echo "Step 1: Creating IAM Roles..."
echo "-----------------------------------------"
bash "${SCRIPT_DIR}/create-iam-roles.sh"
echo ""

echo "Step 2: Creating CodeBuild Project..."
echo "-----------------------------------------"
bash "${SCRIPT_DIR}/create-codebuild-project.sh"
echo ""

echo "Step 3: Creating CodeDeploy Application..."
echo "-----------------------------------------"
bash "${SCRIPT_DIR}/create-codedeploy-app.sh"
echo ""

echo "Step 4: Creating CodeDeploy Deployment Group..."
echo "-----------------------------------------"
bash "${SCRIPT_DIR}/create-codedeploy-deployment-group.sh"
echo ""

echo "Step 5: Creating CodePipeline..."
echo "-----------------------------------------"
bash "${SCRIPT_DIR}/create-codepipeline.sh"
echo ""

echo "========================================="
echo "CI/CD Setup Complete!"
echo "========================================="
echo ""
echo "Pipeline Name: ${CODEPIPELINE_NAME}"
echo "Region: ${AWS_REGION}"
echo ""
echo "To start the pipeline manually, run:"
echo "  aws codepipeline start-pipeline-execution --name ${CODEPIPELINE_NAME} --region ${AWS_REGION}"
echo ""
echo "Or push to GitHub to trigger automatically:"
echo "  git push origin ${GITHUB_BRANCH}"