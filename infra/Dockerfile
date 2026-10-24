# VigilAgent — AWS Lambda container image (ARM64 / Graviton).
# The Lambda Web Adapter lets the stock FastAPI/uvicorn app serve Lambda
# invocations over HTTP without code changes: one image, three runtimes
# (local uvicorn, plain container, Lambda).
FROM public.ecr.aws/awsguru/aws-lambda-adapter:0.9.1 AS adapter
FROM public.ecr.aws/lambda/python:3.12

COPY --from=adapter /lambda-adapter /opt/extensions/lambda-adapter
ENV AWS_LWA_PORT=8080 AWS_LWA_READINESS_CHECK_PATH=/health

WORKDIR /var/task
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ app/
COPY agent/ agent/
COPY tools_cv/ tools_cv/
COPY data/scenes/ data/scenes/

# ENTRYPOINT, not CMD: the lambda/python base image's own entrypoint
# (/lambda-entrypoint.sh) consumes a CMD as a handler name and the
# function dies before the app starts (verified on AWS, 2026-10-24 —
# see evaluation/FAILURE_CASES.md, F6). Overriding the entrypoint lets
# uvicorn receive invocations through the Lambda Web Adapter extension.
ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
