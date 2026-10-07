"""Tests for multi-instance parallel query tools."""

from unittest.mock import Mock

import pytest

from mcp_jenkins.server.multi_instance import (
    get_all_items_multi_instance,
    get_all_nodes_multi_instance,
    get_all_queue_items_multi_instance,
    get_running_builds_multi_instance,
)


@pytest.fixture
def mock_jenkins(mocker):
    mock_jenkins = mocker.Mock()
    mocker.patch("mcp_jenkins.server.multi_instance.jenkins", return_value=mock_jenkins)
    yield mock_jenkins


@pytest.fixture
def multi_instance_ctx(mocker):
    """Mock context with multi-instance configuration."""
    ctx = mocker.Mock()
    lifespan_ctx = mocker.Mock()
    lifespan_ctx.instances.instances = {
        "instance1": mocker.Mock(),
        "instance2": mocker.Mock(),
    }
    ctx.request_context.lifespan_context = lifespan_ctx
    return ctx


@pytest.fixture
def single_instance_ctx(mocker):
    """Mock context without multi-instance configuration."""
    ctx = mocker.Mock()
    lifespan_ctx = mocker.Mock()
    lifespan_ctx.instances = None
    ctx.request_context.lifespan_context = lifespan_ctx
    return ctx


class TestMultiInstanceTools:
    """Test multi-instance parallel query tools."""

    @pytest.mark.asyncio
    async def test_get_all_items_multi_instance_all_instances(
        self, mock_jenkins, multi_instance_ctx
    ):
        """Test getting items from all instances."""
        mock_item = Mock()
        mock_item.model_dump.return_value = {"name": "test-job"}
        mock_jenkins.get_items.return_value = [mock_item]

        result = await get_all_items_multi_instance(multi_instance_ctx)

        assert "instance1" in result
        assert "instance2" in result
        assert result["instance1"] == [{"name": "test-job"}]
        assert result["instance2"] == [{"name": "test-job"}]

    @pytest.mark.asyncio
    async def test_get_all_items_multi_instance_specific_instances(
        self, mock_jenkins, multi_instance_ctx
    ):
        """Test getting items from specific instances."""
        mock_item = Mock()
        mock_item.model_dump.return_value = {"name": "test-job"}
        mock_jenkins.get_items.return_value = [mock_item]

        result = await get_all_items_multi_instance(
            multi_instance_ctx, instances=["instance1"]
        )

        assert "instance1" in result
        assert "instance2" not in result
        assert result["instance1"] == [{"name": "test-job"}]

    @pytest.mark.asyncio
    async def test_get_all_items_multi_instance_no_config(
        self, mock_jenkins, single_instance_ctx
    ):
        """Test error when multi-instance mode not enabled."""
        with pytest.raises(ValueError, match="Multi-instance mode not enabled"):
            await get_all_items_multi_instance(single_instance_ctx)

    @pytest.mark.asyncio
    async def test_get_running_builds_multi_instance(
        self, mock_jenkins, multi_instance_ctx
    ):
        """Test getting running builds from multiple instances."""
        mock_build = Mock()
        mock_build.model_dump.return_value = {"number": 123}
        mock_jenkins.get_running_builds.return_value = [mock_build]

        result = await get_running_builds_multi_instance(multi_instance_ctx)

        assert "instance1" in result
        assert "instance2" in result
        assert result["instance1"] == [{"number": 123}]

    @pytest.mark.asyncio
    async def test_get_all_nodes_multi_instance(self, mock_jenkins, multi_instance_ctx):
        """Test getting nodes from multiple instances."""
        mock_node = Mock()
        mock_node.model_dump.return_value = {"name": "master"}
        mock_jenkins.get_nodes.return_value = [mock_node]

        result = await get_all_nodes_multi_instance(multi_instance_ctx)

        assert "instance1" in result
        assert "instance2" in result
        assert result["instance1"] == [{"name": "master"}]

    @pytest.mark.asyncio
    async def test_get_all_queue_items_multi_instance(
        self, mock_jenkins, multi_instance_ctx
    ):
        """Test getting queue items from multiple instances."""
        mock_queue_item = Mock()
        mock_queue_item.model_dump.return_value = {"id": 456}
        mock_queue = Mock()
        mock_queue.items = [mock_queue_item]
        mock_jenkins.get_queue.return_value = mock_queue

        result = await get_all_queue_items_multi_instance(multi_instance_ctx)

        assert "instance1" in result
        assert "instance2" in result
        assert result["instance1"] == [{"id": 456}]
