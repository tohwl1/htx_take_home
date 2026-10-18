# Reference API chart

Deploys a Secret-backed HTTPS API on an existing EKS platform: three replicas,
resource limits, non-root/read-only containers, disabled service-account tokens,
health probes, topology spreading, a disruption budget and default-deny network
policies with explicit allowances. An internal ALB exposes only `/v1/reference/`.

Replace dummy image/AWS/DNS values before deployment. `image.digest` must be a
published SHA-256 digest; the all-zero default only supports rendering.
Set the real Terraform SG output and existing ACM certificate/private subnet IDs.
Use the target SG that actually protects pod-IP traffic.
The values schema requires CPU/memory requests and limits; tune them using load
tests. Replica and resource settings do not establish capacity or availability.

## External Secrets

Create namespace `reference-api` if absent. Copy `.env.example` to ignored `.env`,
replace the token placeholder and keep only the `API_TOKEN` entry. From the repo root:

```sh
kubectl create namespace reference-api
kubectl -n reference-api create secret generic reference-api-token --from-env-file=.env
kubectl -n reference-api create secret tls reference-api-tls --cert=tls.crt --key=tls.key
kubectl -n reference-api create secret generic reference-api-telemetry-ca --from-file=ca.crt=collector-ca.crt
```

Obtain `tls.crt`/`tls.key` from platform PKI outside Git. The certificate should
cover the service DNS name used for verified internal clients; include required
intermediate certificates. Helm references these Secrets through
`auth.existingSecret` and `tls.existingSecret`; it does not create their values.
Obtain `collector-ca.crt` from the platform team. The chart mounts the CA Secret
configured by `telemetry.caSecret` for verified HTTPS trace export. Missing Secrets
prevent startup. Restrict Secret RBAC and encrypt storage.

Update Secrets and restart all replicas when rotating tokens, certificates or CA bundles:

```sh
kubectl -n reference-api rollout restart deployment/reference-api
kubectl -n reference-api rollout status deployment/reference-api
```

Coordinate clients during mixed-token rollouts. The shared token has no expiry,
per-client identity or scopes; see [authentication](../../README.md#api-authentication).

## Runtime assumptions

ALB uses HTTPS to pods but does not validate backend certificates. The API exports
traces over HTTPS with a mounted trusted CA. The existing Collector must support
that endpoint; see [platform integration](../../README.md).
Health/metrics are unauthenticated internal endpoints; network rules permit the
configured VPC and `telemetry.namespace` to reach port 8443. Collector egress uses
`telemetry.port` in that namespace; it must match the endpoint port.

Topology constraints require suitable existing node/zone capacity. The disruption
budget covers voluntary disruptions only. Reserve surge capacity and test ALB
registration/draining, network-policy behavior and rollouts with real traffic.
The [platform repository](../../README.md#argo-cd-handoff) owns the Argo Application;
this repository supplies only the API chart.
