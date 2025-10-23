"""Tests for pyqwikswitch package."""

from typing import Any

from pyqwikswitch.qwikswitch import (
    QSDevices,
    QSType,
    decode_humidity,
    decode_temperature,
)


def test_qwikcord(example_devices: QSDevices) -> None:
    """Test QwikSwitch devices."""
    assert len(example_devices) == 14
    qc = example_devices["@400001"]
    assert qc.name == "Qwikcord Off?"
    assert qc.qstype == QSType.relay


def test_hum(example_devices: QSDevices) -> None:
    """Test QwikSwitch devices."""
    assert len(example_devices) == 14
    qc = example_devices["@500001"]
    assert qc.name == "Temp Sensor"
    assert qc.qstype == QSType.humidity_temperature
    assert qc.value == -3


def test_listen(example_listen: dict[str, list[dict[str, Any]]]) -> None:
    """Test examples."""
    listen = example_listen["@23c6c0"]
    assert len(listen) > 1

    humidity = [decode_humidity(entry) for entry in listen]

    assert humidity == [62, 72, 66, 58, 32, 75]

    temp = [decode_temperature(entry) for entry in listen]
    assert temp == [23, 23, 23, 23, 15, 15]
