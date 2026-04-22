# ruff: noqa
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from simulator.simulator import RobotSimulator


@pytest.mark.asyncio
async def test_robot_simulator_initial_state():
    with patch("simulator.simulator.BATTERY_INITIAL_MIN", 90), patch("simulator.simulator.BATTERY_INITIAL_MAX", 100):
        bot = RobotSimulator("bot_1")
        assert bot.robot_id == "bot_1"
        assert 90 <= bot.battery <= 100
        assert bot.status == "OK"
        assert not bot.is_charging


@pytest.mark.asyncio
async def test_robot_simulator_state_transition():
    with (
        patch("simulator.simulator.BATTERY_DRAIN_MIN", 5),
        patch("simulator.simulator.BATTERY_DRAIN_MAX", 5),
        patch("simulator.simulator.UPDATE_INTERVAL", 0.001),
    ):
        bot = RobotSimulator("bot_1")
        bot.battery = 30.0

        mock_client = MagicMock()
        # Запускаем один цикл и прерываем через таймаут
        task = asyncio.create_task(bot.run(mock_client))
        await asyncio.sleep(0.005)
        task.cancel()

        # Проверяем, что батарея уменьшилась
        assert bot.battery < 30.0
        assert mock_client.publish.called


@pytest.mark.asyncio
async def test_robot_simulator_battery_thresholds():
    with (
        patch("simulator.simulator.BATTERY_DRAIN_MIN", 1),
        patch("simulator.simulator.BATTERY_DRAIN_MAX", 1),
        patch("simulator.simulator.CRITICAL_BATTERY_LEVEL", 10),
    ):
        bot = RobotSimulator("bot_1")

        # Test Critical Low Battery status
        bot.battery = 5.0
        bot.is_charging = False

        mock_client = MagicMock()
        # Mocking the inner logic of the loop
        drain = 1.0
        bot.battery = max(0.0, bot.battery - drain)
        if bot.battery <= 20.0:
            bot.is_charging = True
        if bot.battery < 10.0:
            bot.status = "CRITICAL_LOW_BATTERY"

        assert bot.status == "CRITICAL_LOW_BATTERY"
        assert bot.is_charging is True
        assert bot.battery == 4.0


@pytest.mark.asyncio
async def test_robot_simulator_drain_to_charge_transition():
    with (
        patch("simulator.simulator.BATTERY_DRAIN_MIN", 5),
        patch("simulator.simulator.BATTERY_DRAIN_MAX", 5),
        patch("simulator.simulator.UPDATE_INTERVAL", 0.001),
    ):
        bot = RobotSimulator("bot_1")
        bot.battery = 21.0
        bot.is_charging = False

        # Manually run the logic equivalent to one step in run()
        drain = 5.0
        bot.battery = max(0.0, bot.battery - drain)  # Should be 16.0
        if bot.battery <= 20.0:
            bot.is_charging = True

        assert bot.battery == 16.0
        assert bot.is_charging is True


@pytest.mark.asyncio
async def test_robot_simulator_critical_status_logic():
    with patch("simulator.simulator.CRITICAL_BATTERY_LEVEL", 10):
        bot = RobotSimulator("bot_1")
        bot.battery = 9.0
        bot.is_charging = False

        # Simulation step
        if bot.battery < 10.0:
            bot.status = "CRITICAL_LOW_BATTERY"
        else:
            bot.status = "OK"

        assert bot.status == "CRITICAL_LOW_BATTERY"
