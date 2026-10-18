# Task 4: observability and batch runbook

Assume existing OpenTelemetry Collector, Prometheus/Alertmanager, Grafana,
Fluent Bit, Loki and Tempo. API metrics, JSON logs and tracing are implemented;
end-to-end collection and alert delivery have not been verified.

**Mode A.** Monitor request rate, 5xx errors, p95 latency, authentication failures,
resource saturation, pod restarts, ALB health, VPN/DNS and certificate expiry.
Prometheus scrapes internal HTTPS metrics; Fluent Bit sends logs to Loki and OTLP
spans flow through Collector to Tempo. Propagate W3C `traceparent` and a bounded
`x-request-id` from the VM. Correlate logs and traces in Grafana; keep IDs out of
metric labels and tokens/payloads out of logs.

**Mode B.** Carry a batch ID and content hash through upload metadata, queue,
worker logs/traces and database audit. Alert on missed nightly arrival, queue age,
DLQ messages, rejected rows and mismatched committed totals. Trace each processing
attempt separately. Platform owners configure alert recipients, verified telemetry
TLS, access, storage encryption and retention. The API chart uses an HTTPS OTLP
endpoint and mounted CA Secret. The platform repository owns Prometheus scrape
trust and downstream telemetry security; runtime checks remain outstanding.

**Failed nightly transfer runbook.** Confirm cutoff/timezone, batch ID and impact.
Check file completion, uploader logs, VPN/DNS, certificates and credentials. Find
the S3 object and compare its hash/manifest; inspect queue age, worker logs/traces
and DLQ. Quarantine invalid schemas and request corrected input. Restore transient
dependencies, then replay with the same batch ID after checking transaction and
idempotency state. Reconcile expected, committed and rejected totals and confirm
acknowledgement before closing the incident.
