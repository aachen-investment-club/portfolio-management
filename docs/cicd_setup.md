# AWS CodePipeline CI/CD Setup Guide

This guide walks through setting up CodePipeline to connect your GitHub repository with CodeBuild and CodeDeploy for automated Docker-based deployments.

## Prerequisites

- AWS account with appropriate permissions
- GitHub repository with the project code pushed
- EC2 instance running Amazon Linux 2 with Docker installed
- ECR repository created

---

## Step 1: Create ECR Repository

```bash
aws ecr create-repository \
  --repository-name portfolio-management \
  --image-scanning-configuration scanOnPush=true \
  --region eu-central-1
```

Note the repository URI: `<account-id>.dkr.ecr.eu-central-1.amazonaws.com/portfolio-management`

---

## Step 2: Create IAM Roles

### 2.1 CodeBuild Service Role

Create a file `codebuild-role.json`:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "codebuild.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

Create the role and attach policies:
```bash
# Create role
aws iam create-role \
  --role-name CodeBuildPortfolioRole \
  --assume-role-policy-document file://codebuild-role.json

# Attach policies
aws iam attach-role-policy \
  --role-name CodeBuildPortfolioRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser

aws iam attach-role-policy \
  --role-name CodeBuildPortfolioRole \
  --policy-arn arn:aws:iam::aws:policy/AWSCodePipeline_FullAccess
```

### 2.2 CodeDeploy Service Role

```bash
# Create role
aws iam create-role \
  --role-name CodeDeployPortfolioRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": { "Service": "codedeploy.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach policies
aws iam attach-role-policy \
  --role-name CodeDeployPortfolioRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSCodeDeployRole

aws iam attach-role-policy \
  --role-name CodeDeployPortfolioRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly
```

### 2.3 EC2 Instance Role

The EC2 instance needs a role with ECR pull permissions. Attach this inline policy to the instance role:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Step 3: Create CodeBuild Project

```bash
aws codebuild create-project \
  --name portfolio-build \
  --source type=GITHUB,location=https://github.com/<owner>/<repo>.git,buildspec=buildspec.yml \
  --artifacts type=CODEPIPELINE \
  --environment type=LINUX_CONTAINER,image=aws/codebuild/amazonlinux2-x86_64-standard:5.0,computeType=BUILD_GENERAL1_SMALL,privilegedMode=true \
  --service-role arn:aws:iam::<account-id>:role/CodeBuildPortfolioRole \
  --region eu-central-1
```

**Important:** `privilegedMode=true` is required for Docker builds.

---

## Step 4: Create CodeDeploy Application & Deployment Group

```bash
# Create application
aws deploy create-application \
  --application-name portfolio-app \
  --compute-platform EC2 \
  --region eu-central-1

# Create deployment group
aws deploy create-deployment-group \
  --application-name portfolio-app \
  --deployment-group-name portfolio-prod \
  --service-role-arn arn:aws:iam::<account-id>:role/CodeDeployPortfolioRole \
  --ec2-tag-filters Key=Name,Value=portfolio-server,Type=KEY_AND_VALUE \
  --deployment-style deploymentType=IN_PLACE,deploymentOption=WITHOUT_TRAFFIC_CONTROL \
  --region eu-central-1
```

---

## Step 5: Create CodePipeline

```bash
aws codepipeline create-pipeline \
  --cli-input-json file://pipeline.json \
  --region eu-central-1
```

Create `pipeline.json`:
```json
{
  "pipeline": {
    "name": "portfolio-pipeline",
    "roleArn": "arn:aws:iam::<account-id>:role/CodeBuildPortfolioRole",
    "artifactStore": {
      "type": "S3",
      "location": "codepipeline-artifacts-<account-id>"
    },
    "stages": [
      {
        "name": "Source",
        "actions": [
          {
            "name": "GitHubSource",
            "actionTypeId": {
              "category": "Source",
              "owner": "ThirdParty",
              "provider": "GitHub",
              "version": "1"
            },
            "outputArtifacts": [{ "name": "SourceArtifact" }],
            "configuration": {
              "Owner": "<github-owner>",
              "Repo": "<repo-name>",
              "Branch": "main",
              "OAuthToken": "<github-personal-access-token>"
            },
            "runOrder": 1
          }
        ]
      },
      {
        "name": "Build",
        "actions": [
          {
            "name": "CodeBuild",
            "actionTypeId": {
              "category": "Build",
              "owner": "AWS",
              "provider": "CodeBuild",
              "version": "1"
            },
            "inputArtifacts": [{ "name": "SourceArtifact" }],
            "outputArtifacts": [{ "name": "BuildArtifact" }],
            "configuration": {
              "ProjectName": "portfolio-build"
            },
            "runOrder": 1
          }
        ]
      },
      {
        "name": "Deploy",
        "actions": [
          {
            "name": "CodeDeploy",
            "actionTypeId": {
              "category": "Deploy",
              "owner": "AWS",
              "provider": "CodeDeploy",
              "version": "1"
            },
            "inputArtifacts": [{ "name": "BuildArtifact" }],
            "configuration": {
              "ApplicationName": "portfolio-app",
              "DeploymentGroupName": "portfolio-prod"
            },
            "runOrder": 1
          }
        ]
      }
    ]
  }
}
```

---

## Step 6: EC2 Instance Setup

### 6.1 Install CodeDeploy Agent

SSH into your EC2 instance:
```bash
sudo yum update -y
sudo yum install -y ruby wget
wget https://aws-codedeploy-eu-central-1.s3.eu-central-1.amazonaws.com/latest/install
chmod +x ./install
sudo ./install auto
sudo systemctl start codedeploy-agent
sudo systemctl status codedeploy-agent
```

### 6.2 Install Docker

```bash
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ec2-user
```

### 6.3 Create Data Directory for Database

```bash
sudo mkdir -p /data
sudo chown ec2-user:ec2-user /data
```

---

## Step 7: Configure Environment Variables

### 7.1 On EC2 Instance

Create `/home/ec2-user/portfolio-management/.env`:
```bash
ENVIRONMENT=production
API_ROUTE=https://your-domain.com
COGNITO_USER_POOL_ID=eu-central-1_unKiHP6hh
COGNITO_CLIENT_ID=your-client-id
COGNITO_DOMAIN_PREFIX=your-domain
AWS_COGNI_CLIENT_SECRET=your-secret
FLASK_SECRET_KEY=your-secret-key
AWS_REGION=eu-central-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
SENTRY_DSN=https://your-sentry-dsn
APCA_API_KEY_ID=your-alpaca-key
APCA_API_SECRET_KEY=your-alpaca-secret
DB_PATH=sqlite:////data/market.db
```

### 7.2 For Deploy Script

Set before running deploy or add to CI/CD environment:
```bash
export ECR_REPO_URI=<account-id>.dkr.ecr.eu-central-1.amazonaws.com/portfolio-management
export AWS_REGION=eu-central-1
```

---

## Step 8: Trigger Pipeline

```bash
# Start pipeline manually
aws codepipeline start-pipeline-execution \
  --name portfolio-pipeline \
  --region eu-central-1

# Or push to GitHub to trigger automatically
git push origin main
```

---

## Troubleshooting

### CodeBuild fails with Docker permission denied
- Ensure `privilegedMode=true` in CodeBuild project settings

### CodeDeploy fails to pull image
- Check EC2 instance role has ECR permissions
- Verify ECR_REPO_URI is correct

### Database not persisting
- Ensure `/data` directory exists on EC2 host
- Check Docker volume mount in deploy.sh

### CodeDeploy agent not running
```bash
sudo systemctl status codedeploy-agent
sudo systemctl restart codedeploy-agent
```

---

## Architecture Flow

```
GitHub Push → CodePipeline → CodeBuild (Docker build + push to ECR)
                                    ↓
                              CodeDeploy (pull from ECR, run on EC2)
                                    ↓
                              Flask app serving on port 80
                              Database at /data/market.db (EC2 host)
```
