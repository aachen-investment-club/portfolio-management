#!/bin/bash

# Copy your repo to EC2
scp -r . ec2-user@<ip>:/home/ec2-user/portfolio

# SSH into EC2
ssh ec2-user@<ip>

# Run the script manually with environment variables
export CONTAINER_NAME="test-app"
export HOST_PORT="5000"
export CONTAINER_PORT="8080"
export DB_HOST_ALIAS="test-db"

cd /home/ec2-user/portfolio
bash scripts/deploy.sh
