# Task 3: CI/CD pipeline

[The workflow](../.github/workflows/pipeline.yaml) has three jobs:

1. **Validate:** on PRs, main pushes and manual runs, execute Python tests,
   Terraform formatting/validation, Checkov and the configuration-risk detector.
   No AWS credentials are available. The detector compares the PR base, previous
   push commit or manual-run parent with HEAD; a missing baseline falls back to
   an empty tree. High risk fails validation. Reports are retained for seven days.
2. **Plan:** after validation, only a manual run on main with `DEPLOY_AWS=true`
   authenticates through AWS OIDC and creates a saved Terraform plan and readable
   `reports/plan.txt`. Both are uploaded together for one day.
3. **Apply:** after the `aws-eks` environment's required approval, download the
   saved plan from the same run and apply it using a separate AWS role.

Separate jobs establish the review boundary and avoid repeating validation.
Checkov supplies static security analysis; Terraform checks formatting and
configuration. Concurrency groups runs by Git ref; S3 lockfiles protect state.
Docker publishing and Kubernetes deployment are separate from this IaC pipeline.

## Setup and use

- Supply the existing secured S3 state bucket and OIDC provider. Restrict plan-role
  trust to `repo:ORG/REPO:ref:refs/heads/main`, apply-role trust to
  `repo:ORG/REPO:environment:aws-eks`, and audience to `sts.amazonaws.com`.
  Grant only the state/lock and EC2 permissions described in [Terraform setup](../infra/README.md).
- Set repository variables `AWS_PLAN_ROLE_ARN`, `AWS_APPLY_ROLE_ARN`,
  `TF_STATE_BUCKET`, `VPC_ID`, `NODE_SECURITY_GROUP_ID`, `VPC_CIDR` and
  `ON_PREMISE_CIDR`. Credentials are temporary; no AWS access keys are committed.
- Configure environment **aws-eks** with required reviewers, main-only deployments,
  prevention of self-review and administrator bypass disabled where supported.
  YAML alone does not require approval. GitHub Free/Pro/Team required reviewers
  are available only for public repositories; private-repository approval needs
  a supported plan or another enforced control. See [GitHub's environment rules](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments).
  Keep state/plans access-restricted; never expose sensitive plans to obtain an approval feature.
- Test the approval gate, then set `DEPLOY_AWS=true`. In Actions, choose
  **Validate, plan and apply Terraform -> Run workflow**, selecting main.
  Download validation and plan artifacts, review the commit, risks and `plan.txt`,
  then select **Review deployments -> aws-eks -> Approve and deploy**.

High-risk changes require correction or a reviewed rule change. Stale state or an
expired plan artifact requires a fresh workflow run and review. Live GitHub/AWS
execution and reviewer enforcement remain unverified.

## Multiple environments

Use separate dev/staging/production inputs, state keys, scoped roles, GitHub
environments and concurrency groups per state. Prefer separate AWS accounts for
isolation and stronger production approval rules. Promote reviewed code between
environments; application releases should reuse the same tested image digest.
