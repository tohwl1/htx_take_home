import json
import subprocess

import pytest
from tools.risk_detector import classify, parse_hcl, run


@pytest.mark.parametrize("address,before,after", [
    ("aws_security_group_rule.api", {}, {"type": "ingress", "cidr_blocks": ["0.0.0.0/0"], "from_port": 443}),
    ("aws_vpc_security_group_ingress_rule.api", {}, {"cidr_ipv6": "::/0"}),
    ("aws_iam_policy.api", {}, {"policy": json.dumps({"Statement": [{"Effect": "Allow", "Action": "s3:*", "Resource": "*"}]})}),
    ("aws_ebs_volume.data", {"encrypted": True}, {"encrypted": False}),
    ("aws_s3_bucket_server_side_encryption_configuration.data", {"rule": [{"apply_server_side_encryption_by_default": [{"kms_master_key_id": "key"}]}]}, {}),
    ("aws_network_acl_rule.api", {}, {"cidr_block": "0.0.0.0/0", "egress": False}),
])
def test_high_risk(address, before, after):
    assert "high" in {x["risk_level"] for x in classify(address, before, after)}


def test_hcl_iam_expression():
    resources = parse_hcl('resource "aws_iam_policy" "bad" { policy = jsonencode({Statement = [{Action = ["*"], Resource = "*", Effect = "Allow"}]}) }')
    assert any(f["risk_level"] == "high" for f in classify("aws_iam_policy.bad", {}, resources["aws_iam_policy.bad"]))


@pytest.mark.parametrize("address", ["aws_security_group.sg", "infra/main.tf:aws_security_group.sg"])
def test_egress_is_not_ingress(address):
    findings = classify(address, {}, {"egress": [{"cidr_blocks": ["0.0.0.0/0"]}]})
    assert not any(f["risk_level"] == "high" for f in findings)


@pytest.mark.parametrize("field", ["Action", "NotAction", "Resource", "NotResource"])
@pytest.mark.parametrize("format", ["json", "hcl"])
def test_wildcard_in_later_policy_list_entry(field, format):
    if format == "json":
        after = {"policy": json.dumps({"Statement": [{field: ["specific", "wildcard*"]}]})}
    else:
        source = f'resource "aws_iam_policy" "bad" {{ policy = jsonencode({{Statement = [{{{field} = ["specific", "wildcard*"]}}]}}) }}'
        after = parse_hcl(source)["aws_iam_policy.bad"]
    assert any(f["risk_level"] == "high" for f in classify("aws_iam_policy.bad", {}, after))


def test_unknown_and_safe():
    assert classify("aws_ebs_volume.data", {}, {}, {"encrypted": True})[0]["risk_level"] == "high"
    assert classify("aws_s3_bucket.data", {"tags": {"Name": "a"}}, {"tags": {"Name": "b"}})[0]["risk_level"] == "low"


def test_exit_codes(tmp_path):
    output = tmp_path / "report.json"
    assert run(["--plan", "tests/fixtures/sample_plan.json", "--output", str(output)]) == 1
    assert {"change_description", "risk_level", "reasoning", "recommendation"} <= json.loads(output.read_text())["findings"][0].keys()
    assert run(["--before", "tests/fixtures/before.tf", "--after", "tests/fixtures/after.tf", "--output", str(output)]) == 1
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{}"); assert run(["--plan", str(invalid), "--output", str(output)]) == 2


def test_git_resource_deletion_and_variable_change(tmp_path, monkeypatch):
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=tmp_path, text=True).strip()
    git("init"); git("config", "user.name", "Test"); git("config", "user.email", "test@example.invalid")
    (tmp_path / "infra/stacks/reference-api").mkdir(parents=True)
    source = tmp_path / "infra/stacks/reference-api/main.tf"
    source.write_text('resource "aws_ebs_volume" "data" { encrypted = true }')
    git("add", "."); git("commit", "-m", "base"); base = git("rev-parse", "HEAD")
    source.write_text('variable "network" { default = "0.0.0.0/0" }')
    git("add", "."); git("commit", "-m", "remove encryption")
    monkeypatch.chdir(tmp_path)
    assert run(["--base", base, "--output", str(tmp_path / "report.json")]) == 1


def test_unsafe_test_fixtures_do_not_block_infrastructure(tmp_path, monkeypatch):
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=tmp_path, text=True).strip()
    git("init"); git("config", "user.name", "Test"); git("config", "user.email", "test@example.invalid")
    (tmp_path / "README.md").write_text("base")
    git("add", "."); git("commit", "-m", "base"); base = git("rev-parse", "HEAD")
    fixtures = tmp_path / "tests/fixtures"
    fixtures.mkdir(parents=True)
    (fixtures / "unsafe.tf").write_text('resource "aws_security_group_rule" "bad" { cidr_blocks = ["0.0.0.0/0"] }')
    git("add", "."); git("commit", "-m", "test fixture")
    monkeypatch.chdir(tmp_path)
    assert run(["--base", base, "--output", str(tmp_path / "report.json")]) == 0
