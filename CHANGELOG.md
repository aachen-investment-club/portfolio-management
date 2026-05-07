# Changelog

All notable changes to this project will be documented in this file.

## [2026-05-07] - CI/CD Pipeline Automation Scripts & Consolidated Documentation

### Documentation
- `docs/ci_cd_pipeline_setup.md` - Consolidated CI/CD setup guide combining:
  - Step-by-step AWS Console instructions
  - AWS CLI-based setup commands
  - Initial service requirements and constraints
  - Organized chronologically: ECR → IAM Roles → CodeBuild → CodeDeploy → CodePipeline → EC2 Setup → Environment Variables → Testing
  - Includes both CLI and Console options for each step
  - Added architecture flow diagram, cost estimates, troubleshooting, and additional notes

### Added

#### IAM Role JSON Files (in `scripts/`)
- `codebuild-role.json` - Trust policy for CodeBuild service role
- `codedeploy-role.json` - Trust policy for CodeDeploy service role
- `ec2-instance-role.json` - Trust policy for EC2 instance role
- `ec2-instance-policy.json` - ECR pull permissions policy for EC2 instances

#### CI/CD Configuration Files (in `scripts/`)
- `cicd.env` - Environment configuration for CI/CD pipeline
  - AWS region, account ID, ECR repository settings
  - GitHub repository owner, name, and branch
  - CodeBuild, CodeDeploy, and CodePipeline resource names
  - **Variables left blank:** `AWS_ACCOUNT_ID`, `GITHUB_OWNER`, `GITHUB_REPO`
- `cicd.secrets` - Secrets configuration (excluded from git via `.gitignore`)
  - GitHub OAuth token, AWS access keys
  - Flask secret key, Cognito client secret
  - Alpaca API credentials, Sentry DSN
  - Cognito configuration, API route
  - **All values left blank**

#### Bash Automation Scripts (in `scripts/`)
- `create-iam-roles.sh` - Creates IAM roles and attaches policies:
  - CodeBuildPortfolioRole with ECR PowerUser and CodePipeline FullAccess
  - CodeDeployPortfolioRole with AWSCodeDeployRole and ECR ReadOnly
  - EC2PortfolioInstanceRole with ECR pull permissions
  - Creates EC2PortfolioInstanceProfile for EC2 instance association
- `create-codebuild-project.sh` - Creates ECR repository and CodeBuild project
- `create-codedeploy-app.sh` - Creates CodeDeploy application (EC2 compute platform)
- `create-codedeploy-deployment-group.sh` - Creates deployment group with EC2 tag filters
- `create-codepipeline.sh` - Generates `pipeline.json` from template and creates CodePipeline
- `run-all.sh` - Master script that runs all setup scripts in sequence with validation

#### Pipeline Template
- `pipeline-template.json` - Template for CodePipeline with placeholders for:
  - AWS Account ID
  - GitHub owner, repo, branch, and OAuth token

### Modified
- `.gitignore` - Added exclusions for `scripts/cicd.secrets` and `scripts/pipeline.json`

### Disclaimer / Prerequisites

- **Before running:** You must fill in the blank values in `scripts/cicd.env` (e.g., `AWS_ACCOUNT_ID`, `GITHUB_OWNER`, `GITHUB_REPO`) and `scripts/cicd.secrets` (e.g., `GITHUB_OAUTH_TOKEN`).
- **AWS CLI:** Ensure the AWS CLI is installed and configured with appropriate credentials (`aws configure`).
- **Permissions:** The AWS user/role used must have permissions to create IAM roles, CodeBuild projects, CodeDeploy applications/deployment groups, and CodePipeline pipelines.

### Usage
1. Fill in blank values in `scripts/cicd.env` and `scripts/cicd.secrets`
2. Run all scripts: `bash scripts/run-all.sh`
3. Or run individual scripts in sequence

After setup is complete, the pipeline will trigger automatically on pushes to your configured GitHub branch, or you can start it manually with:
```bash
aws codepipeline start-pipeline-execution --name portfolio-pipeline --region eu-central-1
```

### Architecture Flow
```
GitHub Push → CodePipeline → CodeBuild (Docker build + push to ECR)
                                    ↓
                              CodeDeploy (pull from ECR, run on EC2)
                                    ↓
                              Flask app serving on port 80
                              Database at /data/market.db (EC2 host)
```
