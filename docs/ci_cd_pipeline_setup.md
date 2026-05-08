# AWS CI/CD Pipeline Setup Guide

This guide consolidates all instructions for setting up a complete CI/CD pipeline using AWS CodePipeline, CodeBuild, and CodeDeploy to automate Docker-based deployments of the portfolio management application.

---

## Overview

### Architecture Flow

```
GitHub Push
    ↓
CodePipeline (orchestrates everything)
    ↓
┌─────────────────────────────────────────┐
│  CodeBuild                              │
│  - Reads buildspec.yml                  │
│  - Builds Docker image                  │
│  - Pushes image to ECR                  │
│  - Outputs appspec.yml + scripts/*      │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  CodeDeploy                             │
│  - Reads appspec.yml                    │
│  - Copies deploy.sh to EC2              │
│  - Runs deploy.sh (ApplicationStart)    │
│    - Pulls image from ECR               │
│    - Stops old container                │
│    - Runs new container on port 80      │
│    - Database persists at /data/        │
└─────────────────────────────────────────┘
    ↓
Flask app serving on EC2 port 80
Database at /data/market.db (EC2 host)
```

### Prerequisites

- AWS account with admin or power-user access
- GitHub repository with the project code pushed
- EC2 instance running Amazon Linux 2 with Docker installed
- AWS CLI installed and configured (for CLI-based setup)


---

## Step 1: Create ECR Repository

### Option A: AWS CLI

```bash
aws ecr create-repository \
  --repository-name portfolio-management \
  --image-scanning-configuration scanOnPush=true \
  --region eu-central-1
```

### Option B: AWS Console

1. Go to AWS Console → Search "ECR" → Click **Amazon ECR**
2. Click **Create repository**
3. Select **Private**
4. Repository name: `portfolio-management`
5. Enable **Scan on push** (recommended)
6. Click **Create repository**
7. **Save the Repository URI** (e.g., `<account-id>.dkr.ecr.eu-central-1.amazonaws.com/portfolio-management`)

---

## Step 2: Create IAM Roles

### 2.1 CodeBuild Service Role

**CLI:**
```bash
aws iam create-role \
  --role-name CodeBuildPortfolioRole \
  --assume-role-policy-document file://scripts/codebuild-role.json

aws iam attach-role-policy \
  --role-name CodeBuildPortfolioRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser

aws iam attach-role-policy \
  --role-name CodeBuildPortfolioRole \
  --policy-arn arn:aws:iam::aws:policy/AWSCodePipeline_FullAccess
```

**Console:**
1. Go to AWS Console → Search "IAM" → Click **IAM**
2. Click **Roles** → Click **Create role**
3. **Trusted entity type**: Select **AWS service**
4. **Use case**: Select **CodeBuild** from the dropdown
5. Add permissions:
   - `AmazonEC2ContainerRegistryPowerUser`
   - `AWSCodePipeline_FullAccess`
   - `CloudWatchLogsFullAccess` (for build logs)
6. Role name: `CodeBuildPortfolioRole`
7. Click **Create role**

### 2.2 CodeDeploy Service Role

**CLI:**
```bash
aws iam create-role \
  --role-name CodeDeployPortfolioRole \
  --assume-role-policy-document file://scripts/codedeploy-role.json

aws iam attach-role-policy \
  --role-name CodeDeployPortfolioRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSCodeDeployRole

aws iam attach-role-policy \
  --role-name CodeDeployPortfolioRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly
```

**Console:**
1. Click **Create role** again
2. **Trusted entity type**: Select **AWS service**
3. **Use case**: Select **CodeDeploy** from the dropdown
4. Add permissions:
   - `AWSCodeDeployRole`
   - `AmazonEC2ContainerRegistryReadOnly`
5. Role name: `CodeDeployPortfolioRole`
6. Click **Create role**

### 2.3 EC2 Instance Role

**CLI:**
```bash
aws iam create-role \
  --role-name EC2PortfolioInstanceRole \
  --assume-role-policy-document file://scripts/ec2-instance-role.json

aws iam put-role-policy \
  --role-name EC2PortfolioInstanceRole \
  --policy-name EC2PortfolioECRPolicy \
  --policy-document file://scripts/ec2-instance-policy.json

aws iam create-instance-profile \
  --instance-profile-name EC2PortfolioInstanceProfile

aws iam add-role-to-instance-profile \
  --instance-profile-name EC2PortfolioInstanceProfile \
  --role-name EC2PortfolioInstanceRole
```

**Console:**
1. Click **Create role**
2. **Trusted entity type**: Select **AWS service**
3. **Use case**: Select **EC2** from the dropdown
4. Add permissions:
   - `AmazonEC2ContainerRegistryReadOnly`
5. Role name: `EC2PortfolioInstanceRole` (or `EC2PortfolioRole`)
6. Click **Create role**
7. Go to AWS Console → Search "EC2" → Click **EC2**
8. Click **Instances** → Select your instance
9. Click **Actions** → **Security** → **Modify IAM role**
10. Select `EC2PortfolioInstanceRole` from dropdown
11. Click **Save**

### 2.4 CodePipeline Service Role

**CLI:**
```bash
aws iam create-role \
  --role-name CodePipelinePortfolioRole \
  --assume-role-policy-document file://scripts/codepipeline-role.json

aws iam attach-role-policy \
  --role-name CodePipelinePortfolioRole \
  --policy-arn arn:aws:iam::aws:policy/AWSCodePipeline_FullAccess
```

**Console:**
1. Click **Create role** again
2. **Trusted entity type**: Select **AWS service**
3. **Use case**: Select **CodePipeline** from the dropdown
4. Add permissions:
   - `AWSCodePipeline_FullAccess`
5. Role name: `CodePipelinePortfolioRole`
6. Click **Create role**

---

## Step 3: Create CodeBuild Project

### Option A: AWS CLI

```bash
aws codebuild create-project \
  --name portfolio-build \
  --source type=GITHUB,location=https://github.com/<owner>/<repo>.git,buildspec=buildspec.yml \
  --artifacts type=CODEPIPELINE \
  --environment "type=LINUX_CONTAINER,image=aws/codebuild/amazonlinux2-x86_64-standard:5.0,computeType=BUILD_GENERAL1_SMALL,privilegedMode=true,environmentVariables=[{name=ECR_REPO_URI,value=<your-ecr-repo-uri>,type=PLAINTEXT}]" \
  --service-role arn:aws:iam::<account-id>:role/CodeBuildPortfolioRole \
  --region eu-central-1
```

**Important:** `privilegedMode=true` is required for Docker builds.

### Option B: AWS Console

1. Go to AWS Console → Search "CodeBuild" → Click **CodeBuild**
2. Click **Create build project**
3. **Project name**: `portfolio-build`
4. **Source**:
   - **Source provider**: Select **GitHub**
   - Connect to your GitHub account and select your repo
   - **Branch**: Select `main`
   - **Buildspec**: Select **Use a buildspec file**
5. **Environment**:
   - **Operating system**: Select **Amazon Linux 2**
   - **Runtime(s)**: Select **Standard**
   - **Image**: Select `aws/codebuild/amazonlinux2-x86_64-standard:5.0` or later
   - **Environment type**: Select **Linux**
   - **Privileged**: ✅ **Check this box** (required for Docker)
   - **Service role**: Select `CodeBuildPortfolioRole`
6. **Environment variables**:
   - **Name**: `ECR_REPO_URI`
   - **Value**: `<your-account-id>.dkr.ecr.eu-central-1.amazonaws.com/portfolio-management`
7. **Artifacts**: Select **CodePipeline**
8. Click **Create build project**

---

## Step 4: Create CodeDeploy Application & Deployment Group

### Option A: AWS CLI

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

### Option B: AWS Console

1. Go to AWS Console → Search "CodeDeploy" → Click **CodeDeploy**
2. Click **Create application**
3. **Application name**: `portfolio-app`
4. **Compute platform**: Select **EC2/On-premises**
5. Click **Create application**
6. Click **Create deployment group**
7. **Deployment group name**: `portfolio-prod`
8. **Service role**: Select `CodeDeployPortfolioRole`
9. **Deployment type**: Select **In-place**
10. **Environment configuration**:
    - Select **Amazon EC2 Instances**
    - **Key**: `Name`
    - **Value**: `portfolio-server` (or whatever tag your EC2 instance has)
11. **Deployment configuration**: Select `CodeDeployDefault.OneAtATime`
12. Skip Load Balancer section
13. Click **Create deployment group**

> ⚠️ **Important:** Make sure you're in the correct region (e.g., `eu-central-1`) in the top-right corner of the AWS Console. CodeDeploy resources are region-specific.

---

## Step 5: Create S3 Artifact Bucket

Before creating the pipeline, you need an S3 bucket for storing artifacts.

**CLI:**
```bash
aws s3api create-bucket \
  --bucket codepipeline-artifacts-<your-account-id> \
  --region eu-central-1 \
  --create-bucket-configuration LocationConstraint=eu-central-1

aws s3api put-bucket-versioning \
  --bucket codepipeline-artifacts-<your-account-id> \
  --versioning-configuration Status=Enabled \
  --region eu-central-1
```

**Console:**
1. Go to AWS Console → Search "S3" → Click **S3**
2. Click **Create bucket**
3. **Bucket name**: `codepipeline-artifacts-<your-account-id>`
4. **Region**: Select `eu-central-1`
5. Disable "Block all public access" (default is fine)
6. Enable **Bucket versioning** (recommended for artifact integrity)
7. Click **Create bucket**

---

## Step 6: Create CodePipeline

### Option A: AWS CLI

The pipeline definition is in `scripts/pipeline-template.json`. Use the provided automation script to generate the final `pipeline.json` and create the pipeline:

```bash
bash scripts/create-codepipeline.sh
```

Or manually:

1. Ensure you have filled in `scripts/cicd.env` and `scripts/cicd.secrets`
2. Generate `pipeline.json` by replacing placeholders in `pipeline-template.json` with your values (account ID, GitHub owner/repo/branch/OAuth token, ECR repository URI)
3. Run:
```bash
aws codepipeline create-pipeline \
  --cli-input-json file://scripts/pipeline.json \
  --region eu-central-1
```

**Important:** The pipeline uses the service role `CodePipelinePortfolioRole` (created in Step 2.4). The pipeline's role ARN must be `arn:aws:iam::<account-id>:role/CodePipelinePortfolioRole`.

### Option B: AWS Console

1. Go to AWS Console → Search "CodePipeline" → Click **CodePipeline**
2. Click **Create pipeline**
3. **Pipeline settings**:
   - **Pipeline name**: `portfolio-pipeline`
   - **Service role**: Select **New service role** (it will create `codepipeline-<pipeline-name>-service-role` automatically)
   - **Execution mode**: Select **Superseded**
   - **Region**: Verify it matches your other resources (e.g., `eu-central-1`)
4. **Source Stage**:
   - **Source provider**: Select **GitHub (Version 2)** — uses GitHub Apps (more secure)
   - **Connection**: Click **Connect to GitHub** and authorize AWS
   - **Repository name**: Select your repo
   - **Branch name**: Select `main`
   - **Detection method**: Select **GitHub webhooks**
5. **Build Stage**:
   - **Build provider**: Select **AWS CodeBuild**
   - **Project name**: Select `portfolio-build`
6. **Deploy Stage**:
   - **Deploy provider**: Select **AWS CodeDeploy**
   - **Application name**: Select `portfolio-app`
   - **Deployment group**: Select `portfolio-prod`
7. Review and click **Create pipeline**

> ❌ **If dropdowns are empty:**
> 1. Verify CodeDeploy application and deployment group are created first
> 2. Verify you're in the **same region** for all resources
> 3. Wait 1-2 minutes after creating CodeDeploy resources, then refresh

---

## Step 7: Prepare EC2 Instance

### 7.1 SSH into Your EC2 Instance

```bash
ssh -i your-key.pem ec2-user@<your-ec2-public-ip>
```

### 7.2 Install CodeDeploy Agent

```bash
sudo yum update -y
sudo yum install -y ruby wget
wget https://aws-codedeploy-eu-central-1.s3.eu-central-1.amazonaws.com/latest/install
chmod +x ./install
sudo ./install auto
sudo systemctl start codedeploy-agent
sudo systemctl status codedeploy-agent
```

You should see: `active (running)`

### 7.3 Install Docker (if not already installed)

```bash
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker ec2-user
```

### 7.4 Create Data Directory for Database

```bash
sudo mkdir -p /data
sudo chown ec2-user:ec2-user /data
```

### 7.5 Set Environment Variable (Optional for manual deployments)

For manual runs of `deploy.sh` (outside of CodePipeline), you need to set `ECR_REPO_URI` in the environment. For pipeline-driven deployments, this is passed automatically.

To set for manual use, add to `~/.bashrc`:

```bash
echo 'export ECR_REPO_URI=<your-account-id>.dkr.ecr.eu-central-1.amazonaws.com/portfolio-management' >> ~/.bashrc
source ~/.bashrc
```

---

## Step 8: Configure Environment Variables

### 8.1 On EC2 Instance

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

### 8.2 For Deploy Script

Set before running deploy or add to CI/CD environment:

```bash
export ECR_REPO_URI=<account-id>.dkr.ecr.eu-central-1.amazonaws.com/portfolio-management
export AWS_REGION=eu-central-1
```

---

## Step 9: Automated Setup (Alternative)

Instead of manual console/CLI setup, you can use the provided automation scripts in the `scripts/` directory:

1. Fill in blank values in `scripts/cicd.env` and `scripts/cicd.secrets`
2. Run all scripts: `bash scripts/run-all.sh`
3. Or run individual scripts in sequence

See [`CHANGELOG.md`](../CHANGELOG.md) for details on the automation scripts.

---

## Step 10: Test the Pipeline

### 10.1 Trigger Manually

**CLI:**
```bash
aws codepipeline start-pipeline-execution \
  --name portfolio-pipeline \
  --region eu-central-1
```

**Console:**
1. Go to CodePipeline → Select `portfolio-pipeline`
2. Click **Release change**
3. Watch the pipeline execute

### 10.2 Automatic Trigger

Push a commit to your GitHub repository:

```bash
git add .
git commit -m "Trigger pipeline"
git push origin main
```

The pipeline will automatically start.

---

## Troubleshooting

### CodeBuild Fails

- **Docker permission denied**: Ensure **Privileged** is checked in CodeBuild environment settings
- **ECR push fails**: Verify `CodeBuildPortfolioRole` has `AmazonEC2ContainerRegistryPowerUser`
- **Buildspec not found**: Ensure `buildspec.yml` is in the root of your repository

### CodeDeploy Fails

- **Agent not found**: Check CodeDeploy agent is running on EC2:
  ```bash
  sudo systemctl status codedeploy-agent
  ```
- **Cannot pull image**: Verify EC2 instance role has ECR permissions attached
- **Script fails**: Check logs at `/opt/codedeploy-agent/deployment-root/<deployment-id>/logs/`

### Pipeline Fails

- **Source not triggering**: Check GitHub connection is active in CodePipeline settings
- **Artifact not found**: Ensure buildspec.yml artifacts section includes `appspec.yml` and `scripts/*`
- **Empty dropdowns in deploy stage**: Verify CodeDeploy resources exist and are in the same region

### Database Not Persisting

- Ensure `/data` directory exists on EC2 host
- Check Docker volume mount in deploy.sh

---

## Additional Notes

- **Database persistence**: The database should be stored on the EC2 instance (not inside Docker) to avoid wipe outs. Use the `--add-host` flag in `docker run` and ensure the `/data` directory is mounted as a volume.
- **Backend ORM refactor**: The database location change may require a small refactor in the backend ORM configuration.
- **Region consistency**: Ensure all resources (ECR, CodeBuild, CodeDeploy, CodePipeline, EC2) are in the same region (`eu-central-1`).
