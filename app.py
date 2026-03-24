import os
import time
import random
from flask import Flask, jsonify
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.resources import Resource

# 配置
OTEL_ENDPOINT = os.getenv("OTEL_ENDPOINT", "http://otel-collector.observability.svc.cluster.local:4317")
APP_NAME = os.getenv("APP_NAME", "testapp")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")

# Resource
resource = Resource.create({
    "service.name": APP_NAME,
    "service.version": APP_VERSION,
})

# Tracer
tracer_provider = TracerProvider(resource=resource)
tracer_provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint=OTEL_ENDPOINT, insecure=True))
)
trace.set_tracer_provider(tracer_provider)
tracer = trace.get_tracer(APP_NAME)

# Meter
metric_reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(endpoint=OTEL_ENDPOINT, insecure=True),
    export_interval_millis=30000
)
meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter(APP_NAME)

# 自定义指标
request_counter = meter.create_counter(
    "testapp_requests_total",
    description="Total requests"
)
error_counter = meter.create_counter(
    "testapp_errors_total",
    description="Total errors"
)

app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)

# 模拟故障开关
FAIL_RATE = int(os.getenv("FAIL_RATE", "0"))  # 0=正常, 33=33%失败
request_count = 0

@app.route("/")
def index():
    return jsonify({
        "service": APP_NAME,
        "version": APP_VERSION,
        "status": "ok"
    })

@app.route("/healthz")
def healthz():
    global request_count
    request_count += 1
    request_counter.add(1, {"endpoint": "healthz"})

    if FAIL_RATE > 0 and request_count % (100 // FAIL_RATE) == 0:
        error_counter.add(1, {"endpoint": "healthz"})
        return jsonify({"status": "error", "version": APP_VERSION}), 500

    return jsonify({"status": "ok", "version": APP_VERSION})

@app.route("/api/data")
def data():
    with tracer.start_as_current_span("process-data") as span:
        span.set_attribute("app.version", APP_VERSION)
        time.sleep(random.uniform(0.01, 0.1))
        request_counter.add(1, {"endpoint": "data"})
        return jsonify({
            "data": [{"id": i, "value": random.randint(1, 100)} for i in range(5)],
            "version": APP_VERSION
        })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
# v2.0.0-bad FAIL_RATE=33
# retry Wed Mar 25 02:29:52 AM CST 2026
