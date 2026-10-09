import pytest

from mcp_jenkins.core.config import JenkinsInstanceConfig, MultiInstanceConfig
from mcp_jenkins.core.lifespan import jenkins, lifespan
from mcp_jenkins.jenkins import Jenkins


class TestLifespan:
    @pytest.fixture(autouse=True, scope="class")
    def mock_jenkins(self, class_mocker):
        class_mocker.patch(
            "mcp_jenkins.core.lifespan.jenkins",
            return_value=Jenkins(
                url="https://jenkins.example.com",
                username="username",
                password="password",
                timeout=5,
                verify_ssl=True,
            ),
        )

    @pytest.mark.asyncio
    async def test_lifespan_context(self, mocker):
        def getenv(key: str, default=None):
            env = {
                "jenkins_url": None,
                "jenkins_username": "username",
                "jenkins_password": None,
                "jenkins_timeout": "5",
                "jenkins_verify_ssl": "true",
                "jenkins_session_singleton": "true",
                "MCP_JENKINS_CONFIG": None,
            }
            return env.get(key, default)

        mocker.patch("mcp_jenkins.core.lifespan.os", mocker.Mock(getenv=getenv))
        async with lifespan(mocker.Mock) as context:
            assert context.jenkins_url is None
            assert context.jenkins_username == "username"
            assert context.jenkins_password is None
            assert context.jenkins_timeout == 5
            assert context.jenkins_verify_ssl is True
            assert context.jenkins_session_singleton is True
            assert context.instances is None


class TestJenkins:
    @pytest.fixture(autouse=True)
    def mock_jenkins(self, mocker):
        return mocker.patch("mcp_jenkins.core.lifespan.Jenkins")

    @pytest.fixture
    def mock_get_http_request(self, mocker):
        return mocker.patch("mcp_jenkins.core.lifespan.get_http_request")

    @pytest.fixture
    def mock_ctx(self, mocker):
        return mocker.Mock(
            request_context=mocker.Mock(
                lifespan_context=mocker.Mock(
                    jenkins_url="https://jenkins.example.com",
                    jenkins_username="username",
                    jenkins_password="password",
                    jenkins_timeout=5,
                    jenkins_verify_ssl=True,
                    jenkins_session_singleton=False,
                    instances=None,
                )
            )
        )

    def test_runtime_error(self, mock_jenkins, mock_get_http_request, mock_ctx):
        mock_get_http_request.side_effect = RuntimeError("Not available http request")

        jenkins(mock_ctx)

        mock_jenkins.assert_called_once_with(
            url="https://jenkins.example.com",
            username="username",
            password="password",
            timeout=5,
            verify_ssl=True,
        )

    def test_exception(self, mock_jenkins, mock_get_http_request, mock_ctx):
        mock_get_http_request.side_effect = Exception("Some other error")

        jenkins(mock_ctx)

        mock_jenkins.assert_called_once_with(
            url="https://jenkins.example.com",
            username="username",
            password="password",
            timeout=5,
            verify_ssl=True,
        )

    def test_retrieves_from_request_state(
        self, mock_jenkins, mock_get_http_request, mock_ctx, mocker
    ):
        mock_get_http_request.return_value = mocker.Mock(
            state=mocker.Mock(
                jenkins_url="https://jenkins.fromrstate.com",
                jenkins_username="state-username",
                jenkins_password="state-password",
            )
        )

        jenkins(mock_ctx)

        mock_jenkins.assert_called_once_with(
            url="https://jenkins.fromrstate.com",
            username="state-username",
            password="state-password",
            timeout=5,
            verify_ssl=True,
        )

    def test_missing_auth(self, mock_get_http_request, mock_ctx):
        mock_get_http_request.side_effect = RuntimeError("Not available http request")
        mock_ctx.request_context.lifespan_context.jenkins_username = None

        with pytest.raises(ValueError):
            jenkins(mock_ctx)

    @pytest.mark.parametrize(('username', 'password'), [(None, None), ('', '')])
    def test_anonymous_credentials(self, mock_jenkins, mock_get_http_request, mock_ctx, username, password):
        mock_get_http_request.side_effect = RuntimeError('No HTTP')
        mock_ctx.request_context.lifespan_context.jenkins_username = username
        mock_ctx.request_context.lifespan_context.jenkins_password = password
        jenkins(mock_ctx)
        mock_jenkins.assert_called_once_with(
            url='https://jenkins.example.com', username=username, password=password, timeout=5, verify_ssl=True
        )

    @pytest.mark.parametrize(('username', 'password'), [('user', None), (None, 'token')])
    def test_partial_credentials_rejected(self, mock_jenkins, mock_get_http_request, mock_ctx, username, password):
        mock_get_http_request.side_effect = RuntimeError('No HTTP')
        mock_ctx.request_context.lifespan_context.jenkins_username = username
        mock_ctx.request_context.lifespan_context.jenkins_password = password
        with pytest.raises(ValueError, match='provided together'):
            jenkins(mock_ctx)
        mock_jenkins.assert_not_called()

    def test_anonymous_missing_url_rejected(self, mock_jenkins, mock_get_http_request, mock_ctx):
        mock_get_http_request.side_effect = RuntimeError('No HTTP')
        mock_ctx.request_context.lifespan_context.jenkins_url = None
        mock_ctx.request_context.lifespan_context.jenkins_username = None
        mock_ctx.request_context.lifespan_context.jenkins_password = None
        with pytest.raises(ValueError, match='URL is required'):
            jenkins(mock_ctx)
        mock_jenkins.assert_not_called()

    def test_merged_header_credentials(self, mock_jenkins, mock_get_http_request, mock_ctx, mocker):
        mock_ctx.request_context.lifespan_context.jenkins_password = None
        mock_get_http_request.return_value = mocker.Mock(
            state=mocker.Mock(jenkins_url=None, jenkins_username=None, jenkins_password='header-token')
        )
        jenkins(mock_ctx)
        mock_jenkins.assert_called_once_with(
            url='https://jenkins.example.com', username='username', password='header-token', timeout=5, verify_ssl=True
        )

    def test_ctx_jenkins_exists(
        self, mock_jenkins, mock_get_http_request, mock_ctx, mocker
    ):
        existing_jenkins = mocker.Mock()

        mock_ctx.request_context.lifespan_context.jenkins_session_singleton = True
        mock_ctx.session.jenkins = existing_jenkins

        assert jenkins(mock_ctx) == existing_jenkins
        mock_jenkins.assert_not_called()


class TestJenkinsMultiInstance:
    @pytest.fixture(autouse=True)
    def mock_jenkins_cls(self, mocker):
        return mocker.patch("mcp_jenkins.core.lifespan.Jenkins")

    @pytest.fixture
    def mock_get_http_request(self, mocker):
        return mocker.patch("mcp_jenkins.core.lifespan.get_http_request")

    @pytest.fixture
    def multi_config(self):
        return MultiInstanceConfig(
            default="prod",
            instances={
                "prod": JenkinsInstanceConfig(
                    url="https://prod.example.com",
                    username="prod_user",
                    password="prod_pass",
                ),
                "dev": JenkinsInstanceConfig(
                    url="https://dev.example.com",
                    username="dev_user",
                    password="dev_pass",
                    timeout=10,
                ),
            },
        )

    @pytest.fixture
    def mock_ctx(self, mocker, multi_config):
        ctx = mocker.Mock()
        ctx.request_context.lifespan_context.instances = multi_config
        ctx.request_context.lifespan_context.jenkins_session_singleton = False
        ctx.session = mocker.Mock(spec=[])
        return ctx

    def test_uses_default_instance(
        self, mock_jenkins_cls, mock_get_http_request, mock_ctx
    ):
        mock_get_http_request.side_effect = RuntimeError("No HTTP")

        jenkins(mock_ctx)

        mock_jenkins_cls.assert_called_once_with(
            url="https://prod.example.com",
            username="prod_user",
            password="prod_pass",
            timeout=5,
            verify_ssl=True,
        )

    def test_uses_explicit_instance(
        self, mock_jenkins_cls, mock_get_http_request, mock_ctx
    ):
        mock_get_http_request.side_effect = RuntimeError("No HTTP")

        jenkins(mock_ctx, instance="dev")

        mock_jenkins_cls.assert_called_once_with(
            url="https://dev.example.com",
            username="dev_user",
            password="dev_pass",
            timeout=10,
            verify_ssl=True,
        )

    def test_unknown_instance_raises(self, mock_get_http_request, mock_ctx):
        mock_get_http_request.side_effect = RuntimeError("No HTTP")

        with pytest.raises(ValueError, match="Unknown Jenkins instance 'nonexistent'"):
            jenkins(mock_ctx, instance="nonexistent")

    def test_instance_from_http_header(
        self, mock_jenkins_cls, mock_get_http_request, mock_ctx, mocker
    ):
        mock_get_http_request.return_value = mocker.Mock(
            state=mocker.Mock(jenkins_instance="dev")
        )

        jenkins(mock_ctx)

        mock_jenkins_cls.assert_called_once_with(
            url="https://dev.example.com",
            username="dev_user",
            password="dev_pass",
            timeout=10,
            verify_ssl=True,
        )

    def test_explicit_instance_overrides_header(
        self, mock_jenkins_cls, mock_get_http_request, mock_ctx, mocker
    ):
        mock_get_http_request.return_value = mocker.Mock(
            state=mocker.Mock(jenkins_instance="dev")
        )

        jenkins(mock_ctx, instance="prod")

        mock_jenkins_cls.assert_called_once_with(
            url="https://prod.example.com",
            username="prod_user",
            password="prod_pass",
            timeout=5,
            verify_ssl=True,
        )

    def test_session_cache_per_instance(
        self, mock_jenkins_cls, mock_get_http_request, mock_ctx, mocker
    ):
        mock_get_http_request.side_effect = RuntimeError("No HTTP")
        mock_ctx.request_context.lifespan_context.jenkins_session_singleton = True

        # First call creates the client
        client1 = jenkins(mock_ctx, instance="prod")
        assert mock_jenkins_cls.call_count == 1

        # Second call returns cached
        client2 = jenkins(mock_ctx, instance="prod")
        assert mock_jenkins_cls.call_count == 1
        assert client1 == client2

        # Different instance creates new client
        jenkins(mock_ctx, instance="dev")
        assert mock_jenkins_cls.call_count == 2

    def test_anonymous_instance_cache_isolated(self, mock_jenkins_cls, mock_get_http_request, mock_ctx, multi_config):
        multi_config.instances['public'] = JenkinsInstanceConfig(url='https://public.example.com')
        mock_get_http_request.side_effect = RuntimeError('No HTTP')
        mock_ctx.request_context.lifespan_context.jenkins_session_singleton = True
        public_client = jenkins(mock_ctx, instance='public')
        mock_jenkins_cls.assert_called_once_with(
            url='https://public.example.com', username=None, password=None, timeout=5, verify_ssl=True
        )
        assert jenkins(mock_ctx, instance='public') is public_client
        jenkins(mock_ctx, instance='prod')
        assert mock_jenkins_cls.call_count == 2
        assert set(mock_ctx.session.jenkins_clients) == {'public', 'prod'}


@pytest.mark.parametrize(('username', 'password'), [('user', None), (None, 'token'), ('', 'token')])
def test_instance_partial_credentials_rejected(username, password):
    with pytest.raises(ValueError, match='provided together'):
        JenkinsInstanceConfig(url='https://example.com', username=username, password=password)
