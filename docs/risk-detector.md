# Task 6: configuration-risk detector

[The Python script](../tools/risk_detector.py) compares committed Terraform
resource blocks under `infra/`, compares two HCL files, or reads Terraform plan
JSON. It assesses proposed configuration changes, not out-of-band AWS drift.
The plan-JSON input meets the assignment's input choice; Git snapshots provide
the pre-plan comparison used in CI. Raw diff parsing and an LLM are not implemented.

After installing `requirements-dev.txt`, run from the repository root:

```sh
python tools/risk_detector.py --base BASE_COMMIT --head HEAD
python tools/risk_detector.py --before tests/fixtures/before.tf --after tests/fixtures/after.tf
python tools/risk_detector.py --plan tests/fixtures/sample_plan.json
```

The fixture commands intentionally report high risk and exit 1. The default output
is `reports/risk-report.json`, containing resource, `change_description`,
`risk_level`, `reasoning` and `recommendation` for each finding.

| Exit code | Meaning |
|---|---|
| 0 | No high findings; medium findings still require review. |
| 1 | High risk; fail CI before planning. |
| 2 | Invalid input, parsing or Git-baseline error; fail CI. |

Rules look for public IPv4/IPv6 ingress, wildcard IAM permissions, encryption
removal and security-sensitive unknown plan values. Network-control changes and
unresolved expressions generally receive medium risk; unmatched changes receive
low risk. Changes to Terraform input/configuration files add a medium finding.
Tests cover the supplied unsafe cases, low-risk changes, deletion, parsing and
exit codes, including wildcards in later IAM list entries and file-prefixed Git
resource addresses. CI only runs source comparison; plan-JSON review is optional locally.

## Known limitations

- Source comparison cannot evaluate Terraform expressions, modules or provider
  defaults. IAM conditions, firewall reachability and all encryption defaults are
  not fully modelled. Low risk is not a safety guarantee.
- JSON policies are inspected structurally. HCL policy expressions use literal
  field/list matching; dynamically constructed permissions still require review.

Checkov and human review complement the detector; they do not establish that its
classification is complete.
