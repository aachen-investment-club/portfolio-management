# Portfolio App – Deployment Guide

This document explains how to deploy the **Portfolio** application to an EC2 instance using:

- **GitHub** (source code)
- **AWS CodePipeline** + **CodeBuild** + **CodeDeploy**
- **Docker** container running on EC2
- **Native PostgreSQL** (on the same EC2 host, not inside Docker)

All tests run **inside the Docker build** – if tests fail, no image is built or deployed.

---

## 📦 Prerequisites

- AWS account with:
  - ECR repository (private)
  - CodePipeline, CodeBuild, CodeDeploy
  - EC2 instance (Amazon Linux 2) with:
    - Docker installed
    - PostgreSQL installed & running (native)
    - CodeDeploy agent installed
- GitHub repository with your code
- IAM roles for CodeBuild (ECR push) and CodeDeploy (ECR pull)

---

## 🚀 Quick overview of the deployment flow

```text
GitHub push (any branch that triggers the pipeline)
    ↓
CodePipeline detects change
    ↓
CodeBuild:
    - runs `docker build` (which internally runs `pytest test/`)
    - if tests pass → image is pushed to ECR
    - if tests fail → build stops, no deployment
    ↓
CodeDeploy:
    - copies `deploy.sh` and `appspec.yml` to EC2
    - executes `deploy.sh` (or a hook in `appspec.yml`)
    - pulls image from ECR, runs container with `--add-host`


# deploy.sh – Container Deployment Script

This script pulls the latest Docker image from Amazon ECR and runs it on an EC2 instance. It is designed for a **native PostgreSQL database running on the same EC2 host** (not inside Docker).

It handles:
- Docker login to ECR
- Pulling the latest `:latest` image
- Stopping/removing any existing container with the same name
- Starting a new container with `--add-host` to connect to the host’s database


## Details on deploy.sh usage

### Run with default values
	./deploy.sh

### Run with custom values
	./deploy.sh <container-name> <host-port> <container-port> <db-alias>
zb 	./deploy.sh prod 80 5000 db-local


### Making executable 
	chmod +x deploy.sh --> gives write permisison


# Manual Deployment

## 1. Build and Test locally
```bash
	docker build -t test
```

## 2. Push to ECR manually
```bash
	# Authenticate
	aws ecr get-login-password --region <region> | docker login --username AWS --password-stdin <ecr-uri>

	# Tag and push
	docker tag portfolio-test <ecr-uri>:latest
	docker push <ecr-uri>:latest
```

## 3. Run on EC2
```bash
# Copy deploy.sh to the instance (or clone the repo there)
scp -i your-key.pem deploy.sh ec2-user@<ec2-ip>:/home/ec2-user/

# On EC2
chmod +x deploy.sh
./deploy.sh myapp 5000 5000 db.local 

```
