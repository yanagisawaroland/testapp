FROM harbor.devops.local:7581/devops/python:3.11-alpine
WORKDIR /app
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple \
    flask==3.0.3 \
    opentelemetry-api==1.24.0 \
    opentelemetry-sdk==1.24.0 \
    opentelemetry-exporter-otlp-proto-grpc==1.24.0 \
    opentelemetry-instrumentation-flask==0.45b0
COPY app.py .
EXPOSE 8080
CMD ["python", "app.py"]
