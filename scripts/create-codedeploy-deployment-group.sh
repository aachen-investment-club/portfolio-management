#!/bin/bash
# create-codedeploy-deployment-group.sh
# Creates the CodeDeploy deployment group

set -e

# Load environment variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/cicd.env"

# Get the AWS account ID if not set
if [ -z "${AWS_ACCOUNT_ID}" ]; then
  AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
  echo "Retrieved AWS Account ID: ${AWS_ACCOUNT_ID}"
fi

echo "=== Creating CodeDeploy Deployment Group ==="

CODEDEPLOY_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/CodeDeployPortfolioRole"

# Create the deployment group
echo "Creating deployment group: ${CODEDEPLOY_DEPLOYMENT_GROUP_NAME}..."

aws deploy create-deployment-group \
  --application-name "${CODEDEPLOY_APP_NAME}" \
  --deployment-group-name "${CODEDEPLOY_DEPLOYMENT_GROUP_NAME}" \
  --service-role-arn "${CODEDEPLOY_ROLE_ARN}" \
  --ec2-tag-filters Key="${EC2_INSTANCE_TAG_NAME}",Value="${EC2_INSTANCE_TAG_VALUE}",Type=KEY_AND_VALUE \
  --deployment-style deploymentType=IN_PLACE,deploymentOption=WITHOUT_TRAFFIC_CONTROL \
  --region "${AWS_REGION}" 2>/dev/null || echo "Deployment group already exists"

echo "=== CodeDeploy Deployment Group Created ==="
echo "Application Name: ${CODEDEPLOY_APP_NAME}"
echo "Deployment Group Name: ${CODEDEPLOY_DEPLOYMENT_GROUP_NAME}"
echo "Service Role ARN: ${CODEDEPLOY_ROLE_ARN}"