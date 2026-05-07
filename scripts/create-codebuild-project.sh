#!/bin/bash
# create-codebuild-project.sh
# Creates the CodeBuild project for building the Docker image

set -e

# Load environment variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/cicd.env"

echo "=== Creating CodeBuild Project ==="

# Get the AWS account ID if not set
if [ -z "${AWS_ACCOUNT_ID}" ]; then
  AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
  echo "Retrieved AWS Account ID: ${AWS_ACCOUNT_ID}"
  ECR_REPO_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"
fi

# Create ECR repository if it doesn't exist
echo "Creating ECR repository if it doesn't exist..."
aws ecr create-repository \
  --repository-name "${ECR_REPO_NAME}" \
  --image-scanning-configuration scanOnPush=true \
  --region "${AWS_REGION}" 2>/dev/null || echo "ECR repository already exists"

# Create the CodeBuild project
echo "Creating CodeBuild project: ${CODEBUILD_PROJECT_NAME}..."

aws codebuild create-project \
  --name "${CODEBUILD_PROJECT_NAME}" \
  --source "type=GITHUB,location=https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}.git,buildspec=buildspec.yml" \
  --artifacts type=CODEPIPELINE \
  --environment "type=LINUX_CONTAINER,image=aws/codebuild/amazonlinux2-x86_64-standard:5.0,computeType=BUILD_GENERAL1_SMALL,privilegedMode=true" \
  --service-role "arn:aws:iam::${AWS_ACCOUNT_ID}:role/CodeBuildPortfolioRole" \
  --region "${AWS_REGION}"

echo "=== CodeBuild Project Created ==="
echo "Project Name: ${CODEBUILD_PROJECT_NAME}"
echo "ECR Repository URI: ${ECR_REPO_URI}"