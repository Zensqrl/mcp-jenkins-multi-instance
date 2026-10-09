from pathlib import Path

import yaml
from pydantic import BaseModel, model_validator


class JenkinsInstanceConfig(BaseModel):
    url: str
    username: str | None = None
    password: str | None = None
    timeout: int = 5
    verify_ssl: bool = True


    @model_validator(mode='after')
    def validate_credentials(self) -> 'JenkinsInstanceConfig':
        if bool(self.username) != bool(self.password):
            msg = 'Jenkins username and password must be provided together or not at all.'
            raise ValueError(msg)
        return self


class MultiInstanceConfig(BaseModel):
    default: str
    instances: dict[str, JenkinsInstanceConfig]

    @model_validator(mode="after")
    def validate_default_exists(self) -> "MultiInstanceConfig":
        if self.default not in self.instances:
            msg = f"Default instance '{self.default}' not found in configured instances: {list(self.instances.keys())}"
            raise ValueError(msg)
        return self


def load_instances_config(path: Path) -> MultiInstanceConfig:
    """Load and validate the multi-instance YAML configuration file.

    Args:
        path: Path to the YAML configuration file.

    Returns:
        Validated MultiInstanceConfig.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If the YAML is invalid or fails validation.
    """
    if not path.exists():
        msg = f"Configuration file not found: {path}"
        raise FileNotFoundError(msg)

    with open(path) as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        msg = f"Configuration file must contain a YAML mapping, got: {type(data).__name__}"
        raise ValueError(msg)

    return MultiInstanceConfig(**data)
