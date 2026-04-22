# ruff: noqa
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from simulator.load_tester import LoadTester


@pytest.fixture
def load_tester():
    return LoadTester()


@pytest.mark.asyncio
async def test_load_tester_worker(load_tester):
    mock_client = MagicMock()
    with patch("simulator.load_tester.create_telemetry_payload", return_value='{"test": 1}'):
        await load_tester.worker(mock_client, messages_to_send=5)

    assert load_tester.sent_count == 5
    assert len(load_tester.latencies) == 5
    assert mock_client.publish.call_count == 5


@pytest.mark.asyncio
async def test_load_tester_run(load_tester):
    # Мокаем MQTTClient
    mock_mqtt_instance = AsyncMock()

    with (
        patch("simulator.load_tester.MQTTClient", return_value=mock_mqtt_instance),
        patch("simulator.load_tester.LOAD_TOTAL_MESSAGES", 10),
        patch("simulator.load_tester.LOAD_CONCURRENCY", 2),
    ):
        await load_tester.run()

    assert load_tester.sent_count == 10
    assert mock_mqtt_instance.connect.called
    assert mock_mqtt_instance.disconnect.called


def test_load_tester_report(load_tester, capsys):
    load_tester.sent_count = 100
    load_tester.start_time = 10.0
    load_tester.end_time = 20.0
    load_tester.latencies = [0.01] * 100

    load_tester.report()
    captured = capsys.readouterr()
    assert "LOAD TEST REPORT" in captured.out
    assert "Total Messages: 100" in captured.out
    assert "Throughput:     10.00 msg/sec" in captured.out
