# ruff: noqa
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from simulator.simulator import main


@pytest.mark.asyncio
async def test_simulator_main_execution():
    mock_mqtt = AsyncMock()
    with (
        patch("simulator.simulator.MQTTClient", return_value=mock_mqtt),
        patch("simulator.simulator.NUM_ROBOTS", 2),
        patch("simulator.simulator.asyncio.gather", new_callable=AsyncMock) as mock_gather,
    ):
        await main()

        assert mock_mqtt.connect.called
        assert mock_gather.called
        # Check that we created 2 simulators
        args = mock_gather.call_args[0]
        assert len(args) == 2
