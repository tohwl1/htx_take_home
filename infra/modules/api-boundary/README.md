# API boundary module

Reusable definitions for one ALB security group and three traffic rules.
It has no provider configuration or backend; the calling stack supplies both.

| Required input | Purpose |
|---|---|
| `name` | Resource name prefix. |
| `vpc_id` | Existing VPC. |
| `vpc_cidr` | Backend destination network on TCP 8443. |
| `on_premise_cidr` | Approved client source network on TCP 443. |
| `node_security_group_id` | Existing SG protecting pod-IP targets. |

Output: `alb_security_group_id`, for the API Helm ingress annotation.
Terraform 1.13+ below 2.0 and AWS provider 6.x are required. Credentials, region
and default tags are inherited from the stack. See [infrastructure setup](../../README.md).
