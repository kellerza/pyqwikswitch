"""Tests for pyqwikswitch package."""

import json
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
from aiohttp import ClientSession
from aioresponses import aioresponses

from pyqwikswitch import QSDevices, QSUsb, qsusb_factory


@pytest.fixture
def mock_aioresponse():
    """Mock aioresponses."""
    with aioresponses() as m:
        yield m


@pytest.fixture
async def qsusb(
    mock_aioresponse: aioresponses,  # mock before the session is created
) -> AsyncGenerator[QSUsb]:
    """Mock Qsusb."""
    async with ClientSession() as session:
        yield await qsusb_factory(
            "http://localhost:2020", 0.123, lambda x, y: None, session
        )


@pytest.fixture
def example_devices() -> QSDevices:
    """Test QwikSwitch devices."""
    devs = QSDevices(
        cb_value_changed=lambda x, y: None, cb_set_qsvalue=lambda x, y, z: None
    )
    examples = Path(__name__).parent.joinpath("example_devices.json")
    with examples.open("r", encoding="utf-8") as f:
        data = json.load(f)
    devs.update_devices(data)
    assert len(devs) == len(data)
    return devs


@pytest.fixture
def example_listen() -> dict[str, list[dict[str, Any]]]:
    """Load example listen data."""
    examples = Path(__name__).parent.joinpath("example_listen.json")
    lines = examples.read_text(encoding="utf-8").splitlines()
    data = dict[str, list[dict[str, Any]]]()
    for line in lines:
        if line.endswith("}"):
            _msg, _, js = line.partition("{")
            entry = json.loads("{" + js)
            data.setdefault(entry["id"], []).append(entry)
    return data
