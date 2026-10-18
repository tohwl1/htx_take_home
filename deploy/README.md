# Link the API to the existing platform

The platform repository owns EKS, Argo CD, observability, certificates and shared
access policies. This repository owns the API Helm chart and its Terraform network
boundary. Nothing here installs or manages the platform services.

## API values

Set `deploy/charts/reference-api/values.yaml` with real inputs, or provide reviewed
`helm.valuesObject` overrides in the platform-owned Argo Application.

| Values | Source |
|---|---|
| `image.repository`, `image.digest` | Separately built/published API image; immutable digest. |
| `ingress.securityGroupId` | This repository's Terraform output. |
| `ingress.host`, `certificateArn`, `subnetIds`, `vpcCidr` | Existing platform network and frontend certificate. |
| `auth.existingSecret`, `tls.existingSecret` | Token and backend TLS Secrets in `reference-api`. |
| `telemetry.endpoint`, `namespace`, `port` | Existing in-cluster Collector HTTPS endpoint and monitoring namespace/port. |
| `telemetry.caSecret` | Secret in `reference-api` containing the Collector CA bundle as `ca.crt`. |

Collector endpoint port and `telemetry.port` must agree. Network policies permit
monitoring ingress and Collector egress in `telemetry.namespace`. The Collector
must actually serve TLS with a certificate matching its hostname. Obtain its CA
from the platform team; the chart mounts it and sets `OTEL_EXPORTER_OTLP_CERTIFICATE`.
Missing Secrets prevent startup. See [Secret setup](charts/reference-api/README.md).

## Argo CD handoff

Add this Application to the **platform repository**, replacing the example URL
and existing project/cluster details. Platform owners supply repository credentials,
project permissions and the API namespace/Secrets. The project must permit the
chart's namespaced workloads, Service, ServiceAccount, Ingress, NetworkPolicies
and PodDisruptionBudget.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: reference-api
  namespace: argocd
spec:
  project: hce-api
  source:
    repoURL: https://github.com/example-org/hce-reference-api.git
    targetRevision: main
    path: deploy/charts/reference-api
    helm:
      releaseName: reference-api
      valueFiles: [values.yaml]
  destination:
    server: https://kubernetes.default.svc
    namespace: reference-api
```

Review and manually sync through the existing Argo CD. Do not also manage the API
with a competing Helm release. This Application example does not configure the
Terraform workflow's separate approval gate.

## Observability handoff

| Existing service | Application integration |
|---|---|
| Prometheus | Discover pods labelled `app=reference-api` in `reference-api`; scrape HTTPS port 8443 at `/metrics/`, trusting the API CA and using a certificate-matching TLS server name. |
| Fluent Bit / Loki | Collect this namespace's JSON stdout logs; retain `request_id` and `trace_id` without creating high-cardinality index labels. |
| Collector / Tempo | Receive API OTLP/HTTP traces over verified HTTPS at the configured endpoint. |
| Grafana / Alertmanager | Use existing data sources and configure the signals/alerts in the [observability design](../docs/observability.md). |

Platform owners configure receiver authorization, downstream encryption, storage
and alert delivery. These settings are handoff requirements, not resources this
chart creates. Runtime ingestion, trust and access controls remain unverified.

## API authentication

Startup requires a nonempty, whitespace-free `API_TOKEN`. Bearer tokens are
compared using `secrets.compare_digest`: missing/invalid tokens return 401, valid
tokens permit all reference reads, and unknown codes return 404. Health and metrics
are unauthenticated internal endpoints. Docker Compose reads ignored `.env`;
Kubernetes uses an external Secret. Never put token values in Git or Helm values.
For direct local development, export `API_TOKEN` before running:

```sh
uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Bare uvicorn does not load `.env`. Rotate the Secret and restart all replicas,
coordinating clients during mixed-token rollouts. The token lacks expiry,
per-client identity, scopes and individual revocation. Planned IdP integration
would validate issuer, audience, expiry and `reference:read`, returning 403 for
insufficient scope and failing closed on validation errors; it is unimplemented.

## Local checks

```sh
helm lint deploy/charts/reference-api -n reference-api
helm template reference-api deploy/charts/reference-api -n reference-api
```

Rendering does not verify real inputs, ALB attachment, TLS, network enforcement,
rollouts or telemetry delivery. Test these with the platform before deployment.
