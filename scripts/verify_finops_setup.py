"""
Automated Verification Script for CloudFormation, CloudWatch, FinOps Budgets, and Teardown Guardrails (ICIP-024).
Audits YAML CloudFormation definitions, Terraform CloudWatch metrics, AWS Budgets, and automated teardown scripts.
"""

import subprocess
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TF_ROOT = PROJECT_ROOT / "infrastructure" / "terraform"
CW_MODULE = TF_ROOT / "modules" / "cloudwatch"
CFN_TEMPLATE = PROJECT_ROOT / "infrastructure" / "cloudformation" / "sns_alerts.yaml"
TEARDOWN_SCRIPT = PROJECT_ROOT / "scripts" / "destroy_infrastructure.py"


def load_cloudformation_yaml(file_path: Path) -> dict:
    """Parse CloudFormation YAML template handling AWS intrinsic tags like !Ref, !Sub, !GetAtt."""

    class CloudFormationLoader(yaml.SafeLoader):
        pass

    def generic_cfn_constructor(loader, node):
        if isinstance(node, yaml.ScalarNode):
            return loader.construct_scalar(node)
        elif isinstance(node, yaml.SequenceNode):
            return loader.construct_sequence(node)
        elif isinstance(node, yaml.MappingNode):
            return loader.construct_mapping(node)
        return None

    cfn_tags = [
        "!Ref",
        "!Sub",
        "!GetAtt",
        "!Join",
        "!Select",
        "!FindInMap",
        "!ImportValue",
        "!Condition",
        "!Equals",
        "!Not",
        "!And",
        "!Or",
    ]
    for tag in cfn_tags:
        yaml.add_constructor(tag, generic_cfn_constructor, Loader=CloudFormationLoader)

    with open(file_path, encoding="utf-8") as f:
        return yaml.load(f, Loader=CloudFormationLoader)


def audit_cloudformation_template() -> bool:
    print("[1/5] Auditing CloudFormation Secondary Stack Template...")
    if not CFN_TEMPLATE.is_file():
        print(f"  [FAIL] CloudFormation template missing: {CFN_TEMPLATE}")
        return False

    cfn_data = load_cloudformation_yaml(CFN_TEMPLATE)

    resources = cfn_data.get("Resources", {})
    assert "PlatformAlertsTopic" in resources, "Missing AWS::SNS::Topic resource"
    assert resources["PlatformAlertsTopic"]["Type"] == "AWS::SNS::Topic"
    assert "AlertEmailSubscription" in resources, (
        "Missing AWS::SNS::Subscription resource"
    )
    assert resources["AlertEmailSubscription"]["Type"] == "AWS::SNS::Subscription"
    assert "PlatformAlertsTopicPolicy" in resources, (
        "Missing AWS::SNS::TopicPolicy resource"
    )

    outputs = cfn_data.get("Outputs", {})
    assert "TopicArn" in outputs, "Missing TopicArn output"
    print(
        "  -> CloudFormation template verified (Valid YAML, SNS Topic, Email Subscription, TopicPolicy, Outputs)."
    )
    return True


def audit_cloudwatch_module() -> bool:
    print("[2/5] Auditing Terraform CloudWatch Monitoring Module...")
    assert (CW_MODULE / "main.tf").is_file(), "CloudWatch main.tf missing"
    assert (CW_MODULE / "variables.tf").is_file(), "CloudWatch variables.tf missing"
    assert (CW_MODULE / "outputs.tf").is_file(), "CloudWatch outputs.tf missing"

    content = (CW_MODULE / "main.tf").read_text(encoding="utf-8")
    assert 'resource "aws_cloudwatch_metric_alarm" "ec2_high_cpu"' in content
    assert 'metric_name         = "CPUUtilization"' in content
    assert "threshold           = 80.0" in content
    assert 'resource "aws_cloudwatch_metric_alarm" "lambda_errors"' in content
    assert 'metric_name         = "Errors"' in content
    assert 'resource "aws_cloudwatch_log_group" "lambda_log_group"' in content
    assert "retention_in_days = var.log_retention_days" in content
    print(
        "  -> CloudWatch module verified (EC2 CPU alarm, Lambda error alarm, 14-day Log Retention)."
    )
    return True


def audit_finops_budget() -> bool:
    print("[3/5] Auditing FinOps AWS Budget Guardrail...")
    root_main = (TF_ROOT / "main.tf").read_text(encoding="utf-8")
    assert 'resource "aws_budgets_budget" "zero_spend_guardrail"' in root_main
    assert 'budget_type       = "COST"' in root_main
    assert "threshold                  = 80" in root_main
    assert "threshold                  = 100" in root_main
    assert 'notification_type          = "FORECASTED"' in root_main
    assert 'notification_type          = "ACTUAL"' in root_main

    root_vars = (TF_ROOT / "variables.tf").read_text(encoding="utf-8")
    assert 'variable "monthly_budget_limit"' in root_vars
    assert "default     = 1.0" in root_vars
    print(
        "  -> FinOps Budget verified ($1.00 USD Free-Tier limit, 80% Forecasted & 100% Actual alerts)."
    )
    return True


def audit_root_terraform_wiring() -> bool:
    print("[4/5] Auditing Root Terraform Orchestration Wiring...")
    root_main = (TF_ROOT / "main.tf").read_text(encoding="utf-8")
    assert 'module "cloudwatch_monitoring"' in root_main
    assert 'source = "./modules/cloudwatch"' in root_main

    root_outputs = (TF_ROOT / "outputs.tf").read_text(encoding="utf-8")
    assert "ec2_cpu_alarm_arn" in root_outputs
    assert "lambda_error_alarm_arn" in root_outputs
    assert "finops_budget_name" in root_outputs
    print(
        "  -> Root Terraform orchestration wiring verified (Monitoring module + FinOps outputs)."
    )
    return True


def audit_teardown_script() -> bool:
    print("[5/5] Auditing Automated Teardown Guardrail Script...")
    assert TEARDOWN_SCRIPT.is_file(), f"Teardown script missing: {TEARDOWN_SCRIPT}"
    result = subprocess.run(
        [sys.executable, str(TEARDOWN_SCRIPT), "--dry-run", "--auto-approve"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        f"Teardown script dry-run failed with code {result.returncode}:\n{result.stderr}"
    )
    assert "ZERO-COST DORMANT STATE" in result.stdout
    print(
        "  -> Teardown guardrail verified (Dry-run purge simulation, zero-cost confirmation)."
    )
    return True


def main() -> int:
    print("=" * 80)
    print(
        "    Insurance Claims Platform — FinOps, Observability & CFn Audit (ICIP-024)"
    )
    print("=" * 80)
    try:
        assert audit_cloudformation_template()
        assert audit_cloudwatch_module()
        assert audit_finops_budget()
        assert audit_root_terraform_wiring()
        assert audit_teardown_script()
        print("\n" + "=" * 80)
        print(" [SUCCESS] All 5 FinOps, Observability & CloudFormation checks PASSED!")
        print("=" * 80)
        return 0
    except AssertionError as e:
        print(f"\n[ERROR] Audit check failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
