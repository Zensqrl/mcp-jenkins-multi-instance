# MCP Jenkins

A fork of [mcp-jenkins](https://github.com/lanbaoshen/mcp-jenkins) with added support for multiple named Jenkins instances.

The Model Context Protocol (MCP) is an open-source implementation that bridges Jenkins with AI language models following Anthropic's MCP specification. This project enables secure, contextual AI interactions with Jenkins tools while maintaining data privacy and security.

## Installation

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

### Setup

```shell
# Clone the repo
git clone https://github.com/steven-lizzi/mcp-jenkins-multi-instance.git
cd mcp-jenkins-multi-instance

# Install dependencies
uv sync
```

### Running the server

```shell
# Single instance (stdio, for use with Copilot/Claude Desktop)
uv run mcp-jenkins --jenkins-url https://jenkins.example.com --jenkins-username alice --jenkins-password <api-token>

# Multi-instance (streamable-http)
uv run mcp-jenkins --config-file ~/.config/mcp-jenkins/instances.yaml --transport streamable-http

# Read-only mode
uv run mcp-jenkins --config-file ~/.config/mcp-jenkins/instances.yaml --read-only --transport streamable-http
```

## CLI Arguments
| Argument                                                     | Description                                                                                                     | Required |
|--------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------|----------|

| Argument                                                     | Description                                                                                                     | Required |
|--------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------|----------|
| `--jenkins-url`                                              | The URL of the Jenkins server. (Http app can set it via headers `x-jenkins-url`)                                | No       |
| `--jenkins-username`                                         | The username for Jenkins authentication. (Http app can set it via headers `x-jenkins-username`)                 | No       |
| `--jenkins-password`                                         | The password or API token for Jenkins authentication. (Http app can set it via headers `x-jenkins-password`)    | No       |
| `--jenkins-timeout`                                          | Timeout for Jenkins API requests in seconds. Default is `5` seconds.                                            | No       |
| `--jenkins-verify-ssl/--no-jenkins-verify-ssl`               | Whether to verify SSL certificates when connecting to Jenkins. Default is to verify.                            | No       |
| `--jenkins-session-singleton/--no-jenkins-session-singleton` | Whether to use a singleton Jenkins client for all requests in the same session. Default is True.                | No       |
| `--config-file`                                              | Path to a YAML file defining multiple named Jenkins instances. Activates multi-instance mode.                   | No       |
| `--read-only`                                                | Whether to enable read-only mode. Default is False                                                              | No       |
| `--transport`                                                | Transport method to use for communication. Options are `stdio`, `sse` or `streamable-http`. Default is `stdio`. | No       |
| `--host`                                                     | Host address for `streamable-http` transport. Default is `0.0.0.0`                                              | No       |
| `--port`                                                     | Port number for `streamable-http` transport. Default is `9887`.                                                 | No       |

## Configuration and Usage

### Jetbrains Github Copilot
1. Open Jetbrains Settings
2. Navigate to Github Copilot > MCP > Configure
3. Add the following configuration:
```json
{
  "servers": {
    "my-mcp-server": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "--directory", "/path/to/mcp-jenkins-multi-instance",
        "run", "mcp-jenkins",
        "--config-file", "/path/to/config/mcp-jenkins/instances.yaml"
      ]
    }
  }
}
```

### VSCode Copilot Chat

#### stdio (recommended for single-user local use)

Add to `.vscode/mcp.json` in your workspace (or `settings.json`):

```json
{
    "servers": {
        "mcp-jenkins": {
            "type": "stdio",
            "command": "uv",
            "args": [
                "--directory", "/path/to/mcp-jenkins-multi-instance",
                "run", "mcp-jenkins",
                "--config-file", "/path/to/config/mcp-jenkins/instances.yaml"
            ]
        }
    }
}
```

For single-instance use, replace `--config-file` with `--jenkins-url`, `--jenkins-username`, and `--jenkins-password` args.

#### SSE / Streamable-HTTP (shared server)

First, start the server:

```shell
# Single instance
uv run mcp-jenkins \
  --jenkins-url xxx \
  --jenkins-username xxx \
  --jenkins-password xxx \
  --transport streamable-http

# Multi-instance
uv run mcp-jenkins \
  --config-file ~/.config/mcp-jenkins/instances.yaml \
  --transport streamable-http
```

Then configure the client in `.vscode/mcp.json`:

- SSE mode
```json
{
    "servers": {
        "mcp-jenkins": {
            "url": "http://localhost:9887/sse",
            "type": "sse"
        }
    }
}
```
- Streamable-HTTP mode
```json
{
    "servers": {
        "mcp-jenkins": {
            "type": "streamableHttp",
            "url": "http://localhost:9887/mcp"
        }
    }
}
```

## Multi-Instance Support

You can connect to multiple Jenkins instances simultaneously using a YAML configuration file.

### Config file format

```yaml
# ~/.config/mcp-jenkins/instances.yaml
default: discover

instances:
  discover:
    url: https://jenkins-discover.example.com
    username: alice
    password: api-token-discover

  analytics:
    url: https://jenkins-analytics.example.com
    username: bob
    password: api-token-analytics
    timeout: 10        # optional, default 5
    verify_ssl: false  # optional, default true
```

### Starting in multi-instance mode

```shell
uvx mcp-jenkins --config-file ~/.config/mcp-jenkins/instances.yaml --transport streamable-http
```

All existing single-instance CLI flags (`--jenkins-url`, etc.) continue to work without a config file.

### Targeting a specific instance

Every tool accepts an optional `instance` parameter. When omitted, the configured `default` instance is used.

```
# List all configured instances
list_instances()

# Target a specific instance
get_all_items(instance="analytics")
get_build(fullname="my-job", instance="discover")
```

For HTTP transports, the instance can also be selected via the `x-jenkins-instance` request header.

> **Security note:** Store your config file with restricted permissions (`chmod 600 ~/.config/mcp-jenkins/instances.yaml`) since it contains credentials.

## Available Tools
| Tool                       | Description                                         |
|----------------------------|-----------------------------------------------------|
| `list_instances`           | List all configured Jenkins instances and the default. |
| `get_item`                 | Get a specific item by name.                        |
| `get_item_config`          | Get the configuration of a specific item.           |
| `set_item_config`          | Set the configuration of a specific item.           |
| `get_item_parameters`      | Get the parameters of a specific item.              |
| `get_all_items`            | Get all items in Jenkins.                           |
| `query_items`              | Query items based on pattern.                       |
| `build_item`               | Build a item.                                       |
| `get_all_nodes`            | Get all nodes in Jenkins.                           |
| `get_node`                 | Get a specific node by name.                        |
| `get_node_config`          | Get the configuration of a specific node.           |
| `set_node_config`          | Set the configuration of a specific node.           |
| `get_all_queue_items`      | Get all queue items in Jenkins.                     |
| `get_queue_item`           | Get a specific queue item by ID.                    |
| `cancel_queue_item`        | Cancel a specific queue item by ID.                 |
| `get_build`                | Get a specific build by job name and build number.  |
| `get_build_scripts`        | Get scripts associated with a specific build.       |
| `get_build_console_output` | Get the console output of a specific build.         |
| `get_build_parameters`     | Get the parameters of a specific build.             |
| `get_build_test_report`    | Get the test report of a specific build.            |
| `get_running_builds`       | Get all currently running builds in Jenkins.        |
| `stop_build`               | Stop a specific build by job name and build number. |
| `get_all_build_artifacts`  | List the artifacts of a specific build.             |
| `get_build_artifact`       | Download an artifact from a specific build.         |
| `get_build_artifact_url`   | Get the direct URL of an artifact from a specific build. |
| `get_view`                 | Get a specific view by name.                        |
| `get_all_views`            | Get all top-level views from Jenkins.               |
| `get_all_plugins`          | Get all installed plugins.                          |
| `get_plugin`               | Get a specific plugin by short name.                |
| `get_plugins_with_problems`| Get all plugins with configuration problems.        |
| `get_plugins_with_backup`  | Get plugins that can be downgraded.                 |
| `get_plugins_with_updates` | Get plugins that have available updates.            |
| `get_plugin_dependency_graph` | Get the dependency graph for a specific plugin.  |

All tools accept an optional `instance` parameter to target a specific Jenkins instance when running in multi-instance mode. The multi-instance parallel tools automatically query all configured instances or a specified subset in parallel for improved performance.


## Contributing
[CONTRIBUTING.md](CONTRIBUTING.md)

## License
Licensed under MIT - see [LICENSE](LICENSE) file. This is not an official Jenkins product.

## Star History
[![Star History Chart](https://api.star-history.com/svg?repos=lanbaoshen/mcp-jenkins&type=Date)](https://www.star-history.com/#lanbaoshen/mcp-jenkins&Date)

### Anonymous Jenkins access

Leave both username and password unset (or empty) to use Jenkins without explicit Basic Auth.
The Jenkins URL is still required; providing only one credential is rejected. This applies
both to legacy CLI/header credentials and each instance in the YAML configuration.
Existing Requests/netrc credential discovery remains unchanged. Jenkins controls the
permissions available to an anonymous user.

Matrix configuration fullnames such as `folder/matrix-job/jdk=17,label=linux` are
addressed using Jenkins' configuration-child URL, without an extra `job/` prefix
before the axis values. Ordinary job and folder URLs remain unchanged.
