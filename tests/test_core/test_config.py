import pytest

from mcp_jenkins.core.config import (
    JenkinsInstanceConfig,
    MultiInstanceConfig,
    load_instances_config,
)


class TestJenkinsInstanceConfig:
    def test_defaults(self):
        config = JenkinsInstanceConfig(
            url="http://j.example.com", username="u", password="p"
        )
        assert config.timeout == 5
        assert config.verify_ssl is True

    def test_custom_values(self):
        config = JenkinsInstanceConfig(
            url="http://j.example.com",
            username="u",
            password="p",
            timeout=10,
            verify_ssl=False,
        )
        assert config.timeout == 10
        assert config.verify_ssl is False


class TestMultiInstanceConfig:
    def test_valid_config(self):
        config = MultiInstanceConfig(
            default="prod",
            instances={
                "prod": JenkinsInstanceConfig(
                    url="http://prod.example.com", username="u", password="p"
                ),
                "dev": JenkinsInstanceConfig(
                    url="http://dev.example.com", username="u2", password="p2"
                ),
            },
        )
        assert config.default == "prod"
        assert len(config.instances) == 2

    def test_default_not_in_instances(self):
        with pytest.raises(ValueError, match="Default instance 'missing' not found"):
            MultiInstanceConfig(
                default="missing",
                instances={
                    "prod": JenkinsInstanceConfig(
                        url="http://prod.example.com", username="u", password="p"
                    ),
                },
            )

    def test_empty_instances(self):
        with pytest.raises(ValueError, match="Default instance 'x' not found"):
            MultiInstanceConfig(default="x", instances={})


class TestLoadInstancesConfig:
    def test_load_valid_yaml(self, tmp_path):
        config_file = tmp_path / "instances.yaml"
        config_file.write_text("""
default: discover

instances:
  discover:
    url: https://jenkins-discover.example.com
    username: alice
    password: token-discover

  analytics:
    url: https://jenkins-analytics.example.com
    username: bob
    password: token-analytics
    timeout: 10
    verify_ssl: false
""")

        config = load_instances_config(config_file)
        assert config.default == "discover"
        assert set(config.instances.keys()) == {"discover", "analytics"}
        assert (
            config.instances["discover"].url == "https://jenkins-discover.example.com"
        )
        assert config.instances["analytics"].timeout == 10
        assert config.instances["analytics"].verify_ssl is False

    def test_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            load_instances_config(tmp_path / "nonexistent.yaml")

    def test_invalid_yaml_content(self, tmp_path):
        config_file = tmp_path / "bad.yaml"
        config_file.write_text("just a string")

        with pytest.raises(ValueError, match="must contain a YAML mapping"):
            load_instances_config(config_file)

    def test_anonymous_instance(self, tmp_path):
        config_file = tmp_path / "incomplete.yaml"
        config_file.write_text("""
default: prod
instances:
  prod:
    url: http://example.com
""")

        config = load_instances_config(config_file)
        assert config.instances["prod"].username is None
        assert config.instances["prod"].password is None

    def test_default_references_missing_instance(self, tmp_path):
        config_file = tmp_path / "bad_default.yaml"
        config_file.write_text("""
default: missing
instances:
  prod:
    url: http://example.com
    username: u
    password: p
""")

        with pytest.raises(ValueError, match="Default instance 'missing' not found"):
            load_instances_config(config_file)


def test_instance_requires_url():
    with pytest.raises(ValueError, match='url'):
        JenkinsInstanceConfig()
