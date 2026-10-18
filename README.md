# HCE hybrid cloud integration

Interview assignment: a hybrid design for an on-premise application calling a
cloud API and uploading nightly CSV files. See [assignment.pdf](assignment.pdf).
The implemented slice is an API network boundary in Terraform, supported by a
small FastAPI service, a CI/CD workflow and a configuration-risk detector.
Batch processing is design-only; the assignment permits partial implementation.

## Assignment navigation

| Task | Deliverable | Status |
|---|---|---|
| 1: architecture | [Design](docs/architecture.md) | Both integration modes, identity, connectivity and trade-offs. |
| 2: IaC | [Terraform](infra/README.md) | One security group and three rules on an existing platform. |
| 3: CI/CD | [Pipeline guide](docs/cicd.md), [workflow](.github/workflows/pipeline.yaml) | Validation, saved plan and environment-gated apply defined; live run and approval setup outstanding. |
| 4: observability | [Monitoring and runbook](docs/observability.md) | Design for both modes; API instrumentation implemented. |
| 5: security | [Three risks and controls](docs/security.md) | Implemented controls and remaining gaps. |
| 6: risk detection | [Detector guide](docs/risk-detector.md), [script](tools/risk_detector.py), [tests](tests/) | Pre-plan risk rules, JSON reports and failure exit codes; regression tests cover IAM lists and Git resource addresses. |

Assume an existing private EKS cluster, VPN, DNS, AWS Load Balancer Controller,
network-policy enforcement, PKI, Argo CD, observability services and secured S3
Terraform state bucket. Platform operators own these prerequisites. Terraform
creates none of them. See [API deployment](deploy/README.md) for integration.

## Local checks

Use Python 3.12 and activate a virtual environment:

```sh
python -m venv .venv
# PowerShell: .venv\Scripts\Activate.ps1
# POSIX: source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pytest
terraform fmt -check -recursive infra
terraform -chdir=infra/stacks/reference-api init -backend=false -lockfile=readonly
terraform -chdir=infra/stacks/reference-api validate
helm lint deploy/charts/reference-api -n reference-api
```

Install Terraform and Helm separately. `requirements.txt` pins direct runtime
packages; `requirements-dev.txt` adds tests and the risk detector. Pip installs
their dependencies automatically; indirect versions are not locked. CI installs
Checkov separately.

Local validation on 18 October 2026: 32 Python tests passed, Terraform formatting
and validation passed, and the API Helm chart passed linting. Checkov
reported 19 passed checks, no failures and one documented SG-attachment suppression.
These checks do not verify live deployment. See the
[detector guide](docs/risk-detector.md) for remaining analysis limitations.

To try the API with Docker, copy `.env.example` to ignored `.env`, replace its
placeholder with a generated token, then run `docker compose up --build`. This
serves local HTTP on `127.0.0.1:8000`; Kubernetes uses HTTPS. Send the token as
`Authorization: Bearer <token>` to `/v1/reference/SGD` or `/v1/reference/USD`.
See [authentication](deploy/README.md#api-authentication) for behavior and rotation.
To inspect plain YAML, run `helm template reference-api deploy/charts/reference-api
--namespace reference-api`. Generated copies under `output/` are ignored by Git;
the Helm chart remains the deployment source.

## Scope and outstanding work

The API uses synthetic in-memory data and a shared token. Short-lived client
identity, batch implementation, live TLS/telemetry verification and AWS/cluster checks
remain outstanding. Example AWS IDs, DNS, repository URLs and image digest are
placeholders. This repository is not a production-ready deployment.

The pipeline validates PRs and main pushes. Separate plan/apply jobs let reviewers
inspect the saved plan before applying that exact file; OIDC avoids stored AWS
keys. Deployment requires a manual run on main, `DEPLOY_AWS=true`, real inputs
and a configured approval gate. Images are built/published separately. Future
environments use separate state, scoped roles and approval rules; see
[CI/CD](docs/cicd.md).

Submission requires committing and pushing the repository, then sharing its link
at least 24 hours before the interview. Sharing the link with the interview panel
is a separate submission step.
