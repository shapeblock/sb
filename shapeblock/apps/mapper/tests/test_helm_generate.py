import unittest
import logging

import yaml

log = logging.getLogger(__name__)

from django.template.loader import render_to_string


class TestGenerateHelmValues(unittest.TestCase):
    def setUp(self):
        self.metadata = {
            "app_uuid": "97b350a1-d27d-4a0a-883c-bc4bd01c934c",
            "cluster_domain": "royal-thunder-445b.shapeblock.xyz",
            "namespace": "drupal-10",
            "git": {
                "url": "https://github.com/shapeblock/drupal-10.git",
                "revision": "main",
            },
            "chart_version": "0.4.8",
        }

        self.sb_yml = {
            "name": "test-123",
            "type": "php",
            "version": "8.1",
            "docroot": "web",
            "envs": {"FOO": "bar", "CONFIG_VARS": '{"test":"hello world"}'},
            "secrets": ["API_KEY", "APP_SALT"],
            "mounts": {"name": "upload-data", "mountPath": "web/sites/default/files", "size": "2Gi", "backup": False},
            "keep": ["templates/*", "assets/*"],
            "services": [{"db1": {"type": "mysql", "version": "10", "size": "2Gi", "backup": False}}],
            "resources": {"cpu": "10m", "memory": "256Mi"},
            "domains": ["www.example.com", "hello.world.com"],
            "workers": {
                "celery": {
                    "resources": {"cpu": "10m", "memory": "256Mi"},
                    "mounts": {
                        "name": "upload-data",
                        "mountPath": "web/sites/default/files",
                        "size": "2Gi",
                        "backup": False,
                    },
                    "envs": {"BAR": "baz"},
                    "secrets": ["EXTERNAL_KEY"],
                }
            },
            "cron": {
                "reports": {
                    "spec": "H * * * *",
                    "timeout": 3600,
                    "resources": {"cpu": "10m", "memory": "256Mi"},
                    "mounts": {
                        "name": "upload-data",
                        "mountPath": "web/sites/default/files",
                        "size": "2Gi",
                        "backup": False,
                    },
                    "envs": {"BAR": "baz"},
                    "secrets": ["EXTERNAL_KEY"],
                }
            },
            "deploy": "set -x -e\ncurl -s https://get.symfony.com/cloud/configurator | bash  \n",
            "post_deploy": "set -x -e\ncurl -s https://get.symfony.com/cloud/configurator | bash  \n",
        }
        deploy_app = render_to_string(f"create-app.yaml", {**self.metadata, **self.sb_yml})
        self.app = yaml.safe_load(deploy_app)
        self.chart_values = yaml.safe_load(self.app["spec"]["chart"]["values"])

    def test_helm_generation_chart_version(self):
        self.assertEqual(self.app["spec"]["chart"]["version"], self.metadata["chart_version"])

    def test_helm_generation_stack_version(self):
        self.assertEqual(
            self.app["spec"]["chart"]["build"][1], {"name": "BP_PHP_VERSION", "value": self.sb_yml["version"]}
        )

    def test_helm_generation_release_prefix(self):
        self.assertEqual(self.chart_values["universal-chart"]["releasePrefix"], self.sb_yml["name"])

    def test_helm_generation_env_vars(self):
        self.assertEqual(self.chart_values["universal-chart"]["envs"]["FOO"], self.sb_yml["envs"]["FOO"])
        self.assertEqual(
            self.chart_values["universal-chart"]["envs"]["CONFIG_VARS"], self.sb_yml["envs"]["CONFIG_VARS"]
        )

    # secrets
    # labels
    # default image
    # default image tag
    # deployment key
    # deployment pod labels
    # deployment replicas
    # deployment resource limits
    # deployment volumes
    # service key
    # service selector labels
    # ingress key
    # pvc
    # hook
    # secret
    # services bind
