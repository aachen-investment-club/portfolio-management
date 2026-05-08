#!/bin/bash
# create-codepipeline.sh
# Creates the CodePipeline using a generated pipeline.json from environment variables

set -e

# Load environment variables and secrets
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/cicd.env"
source "${SCRIPT_DIR}/cicd.secrets"

# Get the AWS account ID if not set
if [ -z "${AWS_ACCOUNT_ID}" ]; then
  AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
  echo "Retrieved AWS Account ID: ${AWS_ACCOUNT_ID}"
fi

# Compute ECR_REPO_URI if not set
if [ -z "${ECR_REPO_URI}" ]; then
  ECR_REPO_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO_NAME}"
  echo "Computed ECR_REPO_URI: ${ECR_REPO_URI}"
fi

echo "=== Creating CodePipeline ==="

# Generate pipeline.json from template
PIPELINE_JSON=$(cat "${SCRIPT_DIR}/pipeline-template.json")

# Replace placeholders with actual values
PIPELINE_JSON="${PIPELINE_JSON//<AWS_ACCOUNT_ID>/${AWS_ACCOUNT_ID}}"
PIPELINE_JSON="${PIPELINE_JSON//<GITHUB_OWNER>/${GITHUB_OWNER}}"
PIPELINE_JSON="${PIPELINE_JSON//<GITHUB_REPO>/${GITHUB_REPO}}"
PIPELINE_JSON="${PIPELINE_JSON//<GITHUB_BRANCH>/${GITHUB_BRANCH}}"
PIPELINE_JSON="${PIPELINE_JSON//<GITHUB_OAUTH_TOKEN>/${GITHUB_OAUTH_TOKEN}}"
PIPELINE_JSON="${PIPELINE_JSON//<ECR_REPO_URI>/${ECR_REPO_URI}}"

# Write the generated JSON to a file
echo "${PIPELINE_JSON}" > "${SCRIPT_DIR}/pipeline.json"

echo "Generated pipeline.json with actual values."

# Create S3 bucket for pipeline artifacts if it doesn't exist
BUCKET_NAME="${CODEPIPELINE_BUCKET}${AWS_ACCOUNT_ID}"
echo "Checking S3 bucket: ${BUCKET_NAME}..."
if aws s3api head-bucket --bucket "${BUCKET_NAME}" --region "${AWS_REGION}" 2>/dev/null; then
  echo "S3 bucket already exists."
else
  echo "Creating S3 bucket: ${BUCKET_NAME}..."
  aws s3api create-bucket \
    --bucket "${BUCKET_NAME}" \
    --region "${AWS_REGION}" \
    --create-bucket-configuration LocationConstraint="${AWS_REGION}"
  # Enable versioning for artifact integrity
  aws s3api put-bucket-versioning \
    --bucket "${BUCKET_NAME}" \
    --versioning-configuration Status=Enabled \
    --region "${AWS_REGION}"
  echo "S3 bucket created and versioning enabled."
fi

# Create the CodePipeline
echo "Creating CodePipeline: ${CODEPIPELINE_NAME}..."

aws codepipeline create-pipeline \
  --cli-input-json file://"${SCRIPT_DIR}/pipeline.json" \
  --region "${AWS_REGION}" 2>/dev/null || echo "CodePipeline already exists"

echo "=== CodePipeline Created ==="
echo "Pipeline Name: ${CODEPIPELINE_NAME}"
echo "S3 Artifact Bucket: ${CODEPIPELINE_BUCKET}${AWS_ACCOUNT_ID}"