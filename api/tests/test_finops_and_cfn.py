"""
Automated Pytest Suite for CloudFormation, CloudWatch, FinOps Budgets, and Teardown Guardrails (ICIP-024).
Validates YAML CloudFormation templates, Terraform CloudWatch monitoring modules, AWS Budgets,
and automated teardown script execution.
"""

from pathlib import Path

import yaml

from scripts.destroy_infrastructure import (
    empty_versioned_s3_bucket,
    run_terraform_destroy,
    teardown_cloudformation_stack,
    verify_prerequisites,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TF_ROOT = PROJECT_ROOT / "infrastructure" / "terraform"
CW_MODULE = TF_ROOT / "modules" / "cloudwatch"
CFN_TEMPLATE = PROJECT_ROOT / "infrastructure" / "cloudformation" / "sns_alerts.yaml"


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


class TestCloudFormationAlertsStack:
    """Validates secondary CloudFormation SNS alert stack template."""

    def test_cloudformation_template_exists(self):
        assert CFN_TEMPLATE.is_file()

    def test_cloudformation_template_valid_yaml(self):
        cfn_data = load_cloudformation_yaml(CFN_TEMPLATE)
        assert cfn_data.get("AWSTemplateFormatVersion") == "2010-09-09"
        assert "Resources" in cfn_data
        assert "Outputs" in cfn_data

    def test_cloudformation_resources_declared(self):
        cfn_data = load_cloudformation_yaml(CFN_TEMPLATE)
        resources = cfn_data["Resources"]
        assert "PlatformAlertsTopic" in resources
        assert resources["PlatformAlertsTopic"]["Type"] == "AWS::SNS::Topic"

        assert "AlertEmailSubscription" in resources
        assert resources["AlertEmailSubscription"]["Type"] == "AWS::SNS::Subscription"

        assert "PlatformAlertsTopicPolicy" in resources
        assert resources["PlatformAlertsTopicPolicy"]["Type"] == "AWS::SNS::TopicPolicy"

    def test_cloudformation_outputs_declared(self):
        cfn_data = load_cloudformation_yaml(CFN_TEMPLATE)
        outputs = cfn_data["Outputs"]
        assert "TopicArn" in outputs
        assert "TopicName" in outputs


class TestCloudWatchMonitoringTerraformModule:
    """Validates Terraform CloudWatch alarms and logging module."""

    def test_cloudwatch_module_files_exist(self):
        assert (CW_MODULE / "main.tf").is_file()
        assert (CW_MODULE / "variables.tf").is_file()
        assert (CW_MODULE / "outputs.tf").is_file()

    def test_cloudwatch_alarms_and_retention(self):
        content = (CW_MODULE / "main.tf").read_text(encoding="utf-8")
        assert 'resource "aws_cloudwatch_metric_alarm" "ec2_high_cpu"' in content
        assert 'metric_name         = "CPUUtilization"' in content
        assert "threshold           = 80.0" in content

        assert 'resource "aws_cloudwatch_metric_alarm" "lambda_errors"' in content
        assert 'metric_name         = "Errors"' in content
        assert "threshold           = 1.0" in content

        assert 'resource "aws_cloudwatch_log_group" "lambda_log_group"' in content
        assert "retention_in_days = var.log_retention_days" in content

    def test_cloudwatch_variables_defaults(self):
        content = (CW_MODULE / "variables.tf").read_text(encoding="utf-8")
        assert 'variable "log_retention_days"' in content
        assert "default     = 14" in content


class TestFinOpsBudgetGuardrail:
    """Validates Terraform FinOps budget resource and root wiring."""

    def test_root_budget_resource_and_alerts(self):
        root_main = (TF_ROOT / "main.tf").read_text(encoding="utf-8")
        assert 'resource "aws_budgets_budget" "zero_spend_guardrail"' in root_main
        assert 'budget_type       = "COST"' in root_main
        assert 'limit_unit        = "USD"' in root_main
        assert 'time_unit         = "MONTHLY"' in root_main
        assert "threshold                  = 80" in root_main
        assert 'notification_type          = "FORECASTED"' in root_main
        assert "threshold                  = 100" in root_main
        assert 'notification_type          = "ACTUAL"' in root_main

    def test_root_terraform_monitoring_wiring_and_outputs(self):
        root_main = (TF_ROOT / "main.tf").read_text(encoding="utf-8")
        assert 'module "cloudwatch_monitoring"' in root_main
        assert 'source = "./modules/cloudwatch"' in root_main

        root_outputs = (TF_ROOT / "outputs.tf").read_text(encoding="utf-8")
        assert "ec2_cpu_alarm_arn" in root_outputs
        assert "lambda_error_alarm_arn" in root_outputs
        assert "finops_budget_name" in root_outputs


class TestAutomatedTeardownGuardrail:
    """Validates automated teardown script execution and safety hooks."""

    def test_teardown_files_exist(self):
        assert (PROJECT_ROOT / "scripts" / "destroy_infrastructure.py").is_file()
        assert (PROJECT_ROOT / "scripts" / "destroy_infrastructure.sh").is_file()

    def test_teardown_prerequisites_check(self):
        assert verify_prerequisites(TF_ROOT) is True

    def test_teardown_dry_run_functions(self):
        assert empty_versioned_s3_bucket("test-bucket", dry_run=True) is True
        assert run_terraform_destroy(TF_ROOT, dry_run=True) is True
        assert teardown_cloudformation_stack("test-stack", dry_run=True) is True
