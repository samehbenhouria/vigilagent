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

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
