import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastmcp import Context, FastMCP
from fastmcp.server.dependencies import get_http_request
from loguru import logger
from pydantic import BaseModel, ConfigDict

from mcp_jenkins.core.config import MultiInstanceConfig, load_instances_config
from mcp_jenkins.jenkins import Jenkins


class LifespanContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    jenkins_url: str | None
    jenkins_username: str | None
    jenkins_password: str | None
    jenkins_timeout: int = 5
    jenkins_verify_ssl: bool = True

    jenkins_session_singleton: bool = True

    instances: MultiInstanceConfig | None = None


@asynccontextmanager
async def lifespan(app: FastMCP[LifespanContext]) -> AsyncIterator["LifespanContext"]:
    jenkins_url = os.getenv("jenkins_url")
    jenkins_username = os.getenv("jenkins_username")
    jenkins_password = os.getenv("jenkins_password")

    jenkins_timeout = int(os.getenv("jenkins_timeout", "5"))
    jenkins_verify_ssl = os.getenv("jenkins_verify_ssl", "true").lower() == "true"
    jenkins_session_singleton = (
        os.getenv("jenkins_session_singleton", "true").lower() == "true"
    )

    instances = None
    config_path = os.getenv("MCP_JENKINS_CONFIG")
    if config_path:
        instances = load_instances_config(Path(config_path))
        logger.info(
            f"Loaded multi-instance config with instances: {list(instances.instances.keys())}"
        )

    yield LifespanContext(
        jenkins_url=jenkins_url,
        jenkins_username=jenkins_username,
        jenkins_password=jenkins_password,
        jenkins_timeout=jenkins_timeout,
        jenkins_verify_ssl=jenkins_verify_ssl,
        jenkins_session_singleton=jenkins_session_singleton,
        instances=instances,
    )


def jenkins(ctx: Context, instance: str | None = None) -> Jenkins:
    lifespan_ctx = ctx.request_context.lifespan_context  # type: ignore[union-attr]
    instances = lifespan_ctx.instances

    if instances:
        # Multi-instance mode
        instance_name = instance
        if not instance_name:
            try:
                requests = get_http_request()
                instance_name = getattr(requests.state, "jenkins_instance", None)
            except (RuntimeError, Exception):  # noqa: BLE001, S110
                pass
        if not instance_name:
            instance_name = instances.default

        if instance_name not in instances.instances:
            msg = f"Unknown Jenkins instance '{instance_name}'. Available: {list(instances.instances.keys())}"
            raise ValueError(msg)

        # Session cache per instance
        if lifespan_ctx.jenkins_session_singleton:
            clients = getattr(ctx.session, "jenkins_clients", None)  # type: ignore[attr-defined]
            if clients and instance_name in clients:
                return clients[instance_name]

        config = instances.instances[instance_name]
        logger.info(
            f'Creating Jenkins client for instance "{instance_name}" with url: '
            f"{config.url}, username: {config.username}, timeout: {config.timeout}, verify_ssl: {config.verify_ssl}"
        )

        client = Jenkins(
            url=config.url,
            username=config.username,
            password=config.password,
            timeout=config.timeout,
            verify_ssl=config.verify_ssl,
        )

        if lifespan_ctx.jenkins_session_singleton:
            if not getattr(ctx.session, "jenkins_clients", None):  # type: ignore[attr-defined]
                ctx.session.jenkins_clients = {}  # type: ignore[attr-defined]
            ctx.session.jenkins_clients[instance_name] = client  # type: ignore[attr-defined]

        return client

    # Legacy single-instance mode
    if lifespan_ctx.jenkins_session_singleton and getattr(ctx.session, "jenkins", None):  # type: ignore[attr-defined]
        return ctx.session.jenkins  # type: ignore[attr-defined]

    jenkins_url = lifespan_ctx.jenkins_url
    jenkins_username = lifespan_ctx.jenkins_username
    jenkins_password = lifespan_ctx.jenkins_password

    jenkins_timeout = lifespan_ctx.jenkins_timeout
    jenkins_verify_ssl = lifespan_ctx.jenkins_verify_ssl

    try:
        requests = get_http_request()

        jenkins_url = getattr(requests.state, "jenkins_url", None) or jenkins_url
        jenkins_username = (
            getattr(requests.state, "jenkins_username", None) or jenkins_username
        )
        jenkins_password = (
            getattr(requests.state, "jenkins_password", None) or jenkins_password
        )

        logger.debug(
            f"Retrieved Jenkins auth from request state - url: {jenkins_url}, username: {jenkins_username}"
        )
    except RuntimeError as e:
        logger.debug(
            f"No HTTP request context available, falling back to environment variables: {e}"
        )
    except Exception as e:  # noqa: BLE001
        logger.error(
            f"Unexpected error retrieving Jenkins auth from request, falling back to environment variables: {e}"
        )

    if not jenkins_url or bool(jenkins_username) != bool(jenkins_password):
        msg = (
            "Jenkins connection details are incomplete: the URL is required, "
            "and username and password must be provided together or not at all. "
            "Please provide them via x-jenkins-* headers "
            "or CLI arguments (--jenkins-url, --jenkins-username, --jenkins-password)."
        )
        raise ValueError(msg)

    logger.info(
        f"Creating Jenkins client with url: "
        f"{jenkins_url}, username: {jenkins_username}, timeout: {jenkins_timeout}, verify_ssl: {jenkins_verify_ssl}"
    )

    ctx.session.jenkins = Jenkins(  # type: ignore[attr-defined]
        url=jenkins_url,
        username=jenkins_username,
        password=jenkins_password,
        timeout=jenkins_timeout,
        verify_ssl=jenkins_verify_ssl,
    )

    return ctx.session.jenkins  # type: ignore[attr-defined]
