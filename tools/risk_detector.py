"""Conservative change triage, not a substitute for a resolved Terraform plan."""
import argparse
import io
import json
from pathlib import Path
import re
import subprocess
import sys

import hcl2

ENCRYPTION = {"encrypted", "storage_encrypted", "enable_encryption", "enable_at_rest_encryption",
              "server_side_encryption_configuration", "kms_key_id", "kms_master_key_id",
              "transit_encryption_enabled", "ssl_enforcement_enabled"}


def walk(value, path=""):
    if isinstance(value, dict):
        for key, child in value.items():
            yield path + "." + key, child
            yield from walk(child, path + "." + key)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield f"{path}[{index}]", child
            yield from walk(child, f"{path}[{index}]")


def report(address, level, reason, recommendation, description):
    return {"resource": address, "change_description": description, "risk_level": level,
            "reasoning": reason, "recommendation": recommendation}


def wildcard_permissions(value):
    if isinstance(value, dict):
        return any((key.lower() in {"action", "notaction", "resource", "notresource"}
                    and "*" in json.dumps(child)) or wildcard_permissions(child)
                   for key, child in value.items())
    if isinstance(value, list):
        return any(wildcard_permissions(child) for child in value)
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            # HCL jsonencode expressions are not JSON; inspect each literal field/list.
            fields = re.finditer(r'\b(?:Action|NotAction|Resource|NotResource)"?\s*[:=]\s*("[^"\n]*"|\[[^\]]*\])', value, re.I)
            return any("*" in match.group(1) for match in fields)
        if isinstance(decoded, (dict, list)):
            return wildcard_permissions(decoded)
    return False


def classify(address, before, after, unknown=None):
    findings = []
    def add(level, reason, recommendation):
        findings.append(report(address, level, reason, recommendation, f"Configuration changed: {address}"))

    before = before or {}
    after = after or {}
    resource_address = address.rsplit(":", 1)[-1]
    kind = resource_address.split(".")[-2] if "." in resource_address else resource_address
    # Scope inspection to ingress blocks where direction is identifiable.
    network = any(x in kind for x in ("security_group", "network_acl", "firewall"))
    relevant = after
    egress_only = "egress" in kind or after.get("type") == "egress" or after.get("egress") is True
    if kind == "aws_security_group":
        relevant = {"ingress": after.get("ingress", [])}
    if network and not egress_only:
        public = [v for _, v in walk(relevant) if isinstance(v, str) and v in {"0.0.0.0/0", "::/0"}]
        if public:
            add("high", "Ingress is reachable from the entire internet.", "Restrict source networks or approved security groups; review exposed ports.")
        elif after:
            add("medium", "Network access changed; verify direction, sources, ports and rule ordering.", "Compare with the approved connectivity design and review the resolved plan.")
    if network and egress_only:
        public = any(v in ("0.0.0.0/0", "::/0") for _, v in walk(after) if isinstance(v, str))
        add("medium", "Outbound firewall rules changed" + (" with an unrestricted destination." if public else "."), "Restrict destinations and ports to workload dependencies.")
    if network and not after:
        add("medium", "A network control was removed; effect depends on remaining rules and ACL order.", "Review reachability and replacement rules before approval.")

    if "iam" in kind or "policy" in kind:
        if wildcard_permissions(after):
            add("high", "IAM policy contains wildcard actions/resources or a wildcard exclusion.", "Scope actions and resource ARNs; document unavoidable wildcards with conditions.")
        elif "${" in json.dumps(after):
            add("medium", "IAM policy contains unresolved expressions; permissions cannot be fully assessed.", "Review resolved policy JSON and run an IAM policy analyzer.")

    old_values = dict(walk(before))
    new_values = dict(walk(after))
    for path, old in old_values.items():
        key = re.sub(r"\[\d+\]", "", path).split(".")[-1]
        if key in ENCRYPTION and old not in (False, None, "", [], {}):
            new = new_values.get(path)
            if new in (False, None, "", [], {}):
                add("high", f"Encryption control {path} was disabled or removed.", "Preserve encryption and approved key ownership; review replacement resources.")
    if unknown and any(v is True for p, v in walk(unknown) if any(k in p for k in ENCRYPTION | {"policy", "cidr", "port"})):
        add("high", "Security-sensitive planned values are unknown.", "Resolve unknown values before treating this change as safe.")
    if not findings:
        expressions = "${" in json.dumps(after)
        add("medium" if expressions else "low",
            "Unresolved Terraform expressions require plan review." if expressions else "No configured high-risk pattern matched; this is not a safety guarantee.",
            "Review the plan, static-analysis findings and application impact.")
    return findings


def parse_hcl(text):
    document = hcl2.load(io.StringIO(text), serialization_options=hcl2.utils.SerializationOptions(strip_string_quotes=True))
    resources = {}
    for block in document.get("resource", []):
        for kind, instances in block.items():
            for name, body in instances.items():
                resources[f"{kind}.{name}"] = body
    return resources


def git(*args, check=True):
    return subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", check=check)


def snapshot(ref, directory="infra"):
    # Inspect all tracked .tf files, including deletions, renames and module source files.
    result = {}
    for name in git("ls-tree", "-r", "--name-only", ref).stdout.splitlines():
        if name.startswith(directory.rstrip("/") + "/") and name.endswith(".tf"):
            for address, body in parse_hcl(git("show", f"{ref}:{name}").stdout).items():
                result[f"{name}:{address}"] = body
    return result


def changes(before, after):
    return [finding for address in sorted(before.keys() | after.keys())
            if before.get(address) != after.get(address)
            for finding in classify(address, before.get(address), after.get(address))]


def run(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, help="terraform show -json output")
    parser.add_argument("--before", type=Path, help="previous .tf fixture")
    parser.add_argument("--after", type=Path, help="proposed .tf fixture")
    parser.add_argument("--base", help="previous committed Git SHA")
    parser.add_argument("--head", default="HEAD", help="proposed committed Git SHA")
    parser.add_argument("--output", type=Path, default=Path("reports/risk-report.json"))
    args = parser.parse_args(argv)
    try:
        if args.plan:
            plan = json.loads(args.plan.read_text())
            if not isinstance(plan.get("resource_changes"), list):
                raise ValueError("plan must contain resource_changes array")
            findings = [item for resource in plan["resource_changes"]
                        if resource["change"]["actions"] != ["no-op"]
                        for item in classify(resource["address"], resource["change"].get("before"),
                                             resource["change"].get("after"), resource["change"].get("after_unknown"))]
        elif args.before and args.after:
            findings = changes(parse_hcl(args.before.read_text()), parse_hcl(args.after.read_text()))
        elif args.base:
            findings = changes(snapshot(args.base), snapshot(args.head))
            # Variable/module/provider changes can alter effective resources without changing their blocks.
            changed_files = git("diff", "--name-only", args.base, args.head).stdout.splitlines()
            config = [f for f in changed_files if f.startswith("infra/") and f.endswith((".tf", ".tfvars", ".tfvars.json", ".hcl"))]
            if config:
                findings.append(report("terraform.configuration", "medium",
                                       "Configuration or inputs changed; source comparison cannot resolve modules, variables or provider defaults.",
                                       "Review the resolved Terraform plan; optional local plan-JSON assessment is available.",
                                       "Changed files: " + ", ".join(config)))
        else:
            raise ValueError("Provide --plan, --before/--after, or --base/--head")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({"findings": findings}, indent=2) + "\n")
        print(json.dumps({"findings": findings}, indent=2))
        return 1 if any(f["risk_level"] == "high" for f in findings) else 0
    except Exception as exc:
        # Parse errors and broken baselines fail closed, never report success.
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({"error": str(exc), "findings": []}, indent=2) + "\n")
        print(f"Risk assessment failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(run())
