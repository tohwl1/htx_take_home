# Task 2: API network boundary

This Terraform slice attaches to an existing EKS/VPN platform. It creates:

| Resource | Purpose |
|---|---|
| ALB security group | Dedicated firewall for the internal API load balancer. |
| ALB ingress rule | TCP 443 from the approved on-premise CIDR. |
| ALB egress rule | TCP 8443 to the configured VPC/pod network. |
| Existing target SG ingress rule | TCP 8443 from the new ALB security group. |

Existing rules on the target security group remain in effect and require review.
The code does not create EKS, an ALB, VPN, VPC, subnets, DNS, certificates, IAM
roles or an S3 state bucket. Helm/Argo and the existing Load Balancer Controller
manage the API and ALB separately.

## Layout and inputs

- [modules/api-boundary](modules/api-boundary/README.md): reusable resource definitions.
- [stacks/reference-api](stacks/reference-api/README.md): deployable root with provider, backend, inputs and lock file.

Supply a real VPC ID, VPC CIDR, approved on-premise CIDR and the existing security
group that protects API pod-IP targets. The example assumes AWS VPC CNI; adapt the
target SG if using security groups for pods. Existing VPN routes, private DNS,
ALB Controller, enforced network policies and PKI are prerequisites.

## Local use

Install Terraform 1.13.x and use the stack directory. The following copy commands
use POSIX shell syntax; PowerShell can use `Copy-Item`.

```sh
cp infra/stacks/reference-api/terraform.tfvars.example infra/stacks/reference-api/eks.tfvars
cp infra/stacks/reference-api/backend.hcl.example infra/stacks/reference-api/backend.hcl
# Replace placeholders and authenticate with an approved AWS profile.
terraform -chdir=infra/stacks/reference-api init -backend-config=backend.hcl
terraform -chdir=infra/stacks/reference-api plan -var-file=eks.tfvars -out=reviewed.tfplan
terraform -chdir=infra/stacks/reference-api show -no-color reviewed.tfplan
# Only after review:
terraform -chdir=infra/stacks/reference-api apply reviewed.tfplan
terraform -chdir=infra/stacks/reference-api output alb_security_group_id
```

Use the output as `ingress.securityGroupId` in the API Helm values. Supply real
subnet IDs, ACM certificate, DNS, image and Secrets through [deployment setup](../deploy/README.md).
Checkov suppresses only `CKV2_AWS_5` for this SG because attachment occurs outside
Terraform; verify the real ALB attachment.

## State and credentials

The S3 backend refers to a dummy existing bucket; it does not create one.
Platform owners supply versioning, encryption, TLS-only access, public-access
blocking and scoped state/lock permissions. Add `kms_key_id` to backend overrides
if required, with scoped KMS permissions. Keep real inputs, state and plans out
of Git. `.terraform.lock.hcl` pins providers; S3 lockfiles coordinate state writes.

Use short-lived AWS credentials. The plan role needs required EC2 Describe calls,
state read and lock create/delete. Apply additionally needs state write and scoped
security-group/rule create, tag, authorize, revoke and delete permissions. Constrain
writes to the intended VPC/project with IAM conditions; required Describe wildcards
are not a reason to grant wildcard actions. Roles and OIDC trust are platform-owned
and must be validated against real resources. See [CI/CD](../docs/cicd.md).
