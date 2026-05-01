


services: 
- create a private repo in ECR (for container registry)
- setup CodePipeline to connect repo with CodeBuild & CodeDeploy
- CodeBuild: define yml file (docker build)
    - setup IAM role for ECR push
- CodeDeploy: create yml file  (docker pull , run...)
    - setup IAM role to pull form ECR


extra constraint: DB should be in EC2; not docker (to avoid wipe outs). 
- in docker run use "--add-host" flag
- this also requires a small refactor in the backend ORM 