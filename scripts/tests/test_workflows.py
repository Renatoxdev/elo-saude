import os
import subprocess
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.deploy = yaml.safe_load((ROOT / ".github/workflows/deploy.yml").read_text())
        self.environment = {
            **os.environ,
            **dict.fromkeys(
                (
                    "AWS_REGION",
                    "AWS_ROLE_ARN",
                    "ECR_REPOSITORY",
                    "ECS_CLUSTER",
                    "ECS_SERVICE",
                    "ECS_TASK_DEFINITION",
                    "ECS_SUBNETS",
                    "ECS_SECURITY_GROUPS",
                ),
                "configured",
            ),
            "GITHUB_REF": "refs/heads/main",
            "DEPLOY_ENVIRONMENT": "production",
            "PROMOTED_IMAGE": "123456789012.dkr.ecr.us-east-1.amazonaws.com/api@sha256:" + "a" * 64,
        }

    def validate(self, **changes):
        return subprocess.run(
            [
                "bash",
                "--noprofile",
                "--norc",
                "-eo",
                "pipefail",
                "-c",
                self.deploy["jobs"]["deploy"]["steps"][0]["run"],
            ],
            env={**self.environment, **changes},
            capture_output=True,
            text=True,
            timeout=5,
        )

    def test_production_requires_a_valid_digest_before_aws_credentials(self):
        for value in (
            "",
            "repo:latest",
            "repo@sha256:" + "a" * 64,
            self.environment["PROMOTED_IMAGE"] + "\nextra",
        ):
            with self.subTest(image=value):
                self.assertNotEqual(self.validate(PROMOTED_IMAGE=value).returncode, 0)
        result = self.validate()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_deploy_rejects_wrong_environment_branch_or_missing_configuration(self):
        for changes in (
            {"DEPLOY_ENVIRONMENT": "preview"},
            {"GITHUB_REF": "refs/heads/feature"},
            {"AWS_ROLE_ARN": ""},
            {"DEPLOY_ENVIRONMENT": "staging"},
        ):
            with self.subTest(changes=changes):
                self.assertNotEqual(self.validate(**changes).returncode, 0)
        self.assertEqual(
            self.validate(DEPLOY_ENVIRONMENT="staging", PROMOTED_IMAGE="").returncode, 0
        )

    def test_workflows_use_shell_that_propagates_pipeline_failures(self):
        for name in ("pipeline", "deploy"):
            workflow = yaml.safe_load((ROOT / f".github/workflows/{name}.yml").read_text())
            self.assertEqual(workflow["defaults"]["run"]["shell"], "bash")
        # Comando real: gzip consegue encerrar mesmo se o produtor falhar.
        result = subprocess.run(
            ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", "false | gzip > /dev/null"],
            timeout=5,
        )
        self.assertNotEqual(result.returncode, 0)
