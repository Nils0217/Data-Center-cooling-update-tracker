import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

resource = Resource.create({"service.name": "cooling-pue-factory"})
provider = TracerProvider(resource=resource)

# 若有設定 SIGNOZ_ENDPOINT 則發送到 SigNoz，否則輸出到終端機日誌
signoz_endpoint = os.getenv("SIGNOZ_ENDPOINT", "http://localhost:4317")

try:
    otlp_exporter = OTLPSpanExporter(endpoint=signoz_endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
except Exception:
    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

trace.set_tracer_provider(provider)
tracer = trace.get_tracer("cooling-pue-factory")
