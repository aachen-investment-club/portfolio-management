# build with: docker build --platform linux/amd64 --provenance=false -t athena-updater-portfolio-management -f lambda_athena_updater.Dockerfile .


FROM public.ecr.aws/lambda/python:3.13

COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install -r requirements.txt


COPY portfolio/ ${LAMBDA_TASK_ROOT}/portfolio/


CMD [ "portfolio.lambda_handler.handler" ]
