#!/bin/bash
# create-iam-roles.sh
# Creates IAM roles and attaches policies for CodeBuild, CodeDeploy, and EC2 Instance

set -e

# Load environment variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/cicd.env"

echo "=== Creating IAM Roles for CI/CD Pipeline ==="

# -------------------------------------------
# 1. Create CodeBuild Service Role
# -------------------------------------------
echo "Creating CodeBuild service role..."

aws iam create-role \
  --role-name CodeBuildPortfolioRole \
  --assume-role-policy-document file://"${SCRIPT_DIR}/codebuild-role.json" \
  --region "${AWS_REGION}" || echo "CodeBuildPortfolioRole already exists"

aws iam attach-role-policy \
  --role-name CodeBuildPortfolioRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser \
  --region "${AWS_REGION}"

aws iam attach-role-policy \
  --role-name CodeBuildPortfolioRole \
  --policy-arn arn:aws:iam::aws:policy/AWSCodePipeline_FullAccess \
  --region "${AWS_REGION}"

echo "CodeBuild service role created."

# -------------------------------------------
# 2. Create CodeDeploy Service Role
# -------------------------------------------
echo "Creating CodeDeploy service role..."

aws iam create-role \
  --role-name CodeDeployPortfolioRole \
  --assume-role-policy-document file://"${SCRIPT_DIR}/codedeploy-role.json" \
  --region "${AWS_REGION}" || echo "CodeDeployPortfolioRole already exists"

aws iam attach-role-policy \
  --role-name CodeDeployPortfolioRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSCodeDeployRole \
  --region "${AWS_REGION}"

aws iam attach-role-policy \
  --role-name CodeDeployPortfolioRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly \
  --region "${AWS_REGION}"

echo "CodeDeploy service role created."

# -------------------------------------------
# 3. Create EC2 Instance Role
# -------------------------------------------
echo "Creating EC2 instance role..."

aws iam create-role \
  --role-name EC2PortfolioInstanceRole \
  --assume-role-policy-document file://"${SCRIPT_DIR}/ec2-instance-role.json" \
  --region "${AWS_REGION}" || echo "EC2PortfolioInstanceRole already exists"

aws iam put-role-policy \
  --role-name EC2PortfolioInstanceRole \
  --policy-name EC2PortfolioECRPolicy \
  --policy-document file://"${SCRIPT_DIR}/ec2-instance-policy.json" \
  --region "${AWS_REGION}"

# Create instance profile for EC2
aws iam create-instance-profile \
  --instance-profile-name EC2PortfolioInstanceProfile \
  --region "${AWS_REGION}" || echo "EC2PortfolioInstanceProfile already exists"

aws iam add-role-to-instance-profile \
  --instance-profile-name EC2PortfolioInstanceProfile \
  --role-name EC2PortfolioInstanceRole \
  --region "${AWS_REGION}" || echo "Role already attached to instance profile"

echo "EC2 instance role created."

echo "=== IAM Roles Creation Complete ==="
