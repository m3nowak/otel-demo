# otel-demo

## Common

Env

 - OTEL_EXPORTER_OTLP_ENDPOINT: Opentelemetry - otlp endpoint address
 - OTEL_EXPORTER_OTLP_USE_GRPC: Opentelemetry - whether use grpc (0/1)
 - OTEL_SERVICE_NAME: Opentelemetry - service name for resource
 - OTEL_SERVICE_NAMESPACE: Opentelemetry - service namespace for resource
 - APP_NATS_URL: Nats url, default `nats://127.0.0.1:4222`

## Exporter

Env
- APP_PORT: GRPC Port of exporter, default 4317
- APP_DB: Database connection info, `username:password@host:5432/dbname`

## Alloy

- GRAFANA_CLOUD_USER_KEY: Grafana cloud user
- GRAFANA_CLOUD_API_KEY: Grafana cloud key
