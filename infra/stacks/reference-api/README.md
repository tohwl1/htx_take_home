# Reference API stack

Run Terraform against this directory. `main.tf` calls the reusable
`api-boundary` module; provider, backend, inputs and provider lock file belong here.
The default region is `ap-southeast-1` and environment label is `eks`.

For validation without remote state or AWS credentials:

```sh
terraform -chdir=infra/stacks/reference-api init -backend=false -lockfile=readonly
terraform -chdir=infra/stacks/reference-api validate
```

Provider installation still needs registry access or a local cache.
For plan/apply, follow [infrastructure setup](../../README.md), replacing the
example inputs and dummy S3 backend bucket. The state key is
`hce/eks/api-boundary.tfstate`, with encryption and native locking enabled.
The stack exports `alb_security_group_id`; it does not provision the existing platform.
