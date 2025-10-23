"""Tests."""

import asyncio
from json import dumps
from unittest.mock import MagicMock, call

from aioresponses import aioresponses

from pyqwikswitch import QSDev, QSDevices, QSUsb


async def test_qsusb_init(qsusb):
    """Test Qsusb."""
    assert qsusb.url == "http://localhost:2020"
    assert qsusb.devices.dim_adj == 0.123


async def test_devices(
    qsusb: QSUsb, mock_aioresponse: aioresponses, example_devices: QSDevices
):
    """Test Qsusb devices."""
    dl = [d.data for d in example_devices.values()]

    mock_aioresponse.get("http://localhost:2020/&device", body=dumps(dl))
    await qsusb.update_from_devices()

    assert len(qsusb.devices) == len(example_devices)


async def test_listen(qsusb: QSUsb, mock_aioresponse: aioresponses):
    """Test Qsusb listen."""
    packet = {
        "cmd": "STATUS.ACK",
        "data": "OFF,RX1REL,V50",
        "id": "@000ba0",
        "rssi": "60%",
    }
    packets = [
        packet,
        dict(packet, data="ON"),
    ]

    listen_url = "http://localhost:2020/&listen"

    for p in packets:
        mock_aioresponse.get(listen_url, body=dumps(p) + "\n")
    mock_aioresponse.get(listen_url, exception=TimeoutError())

    cb = MagicMock(side_effect=lambda a: None)

    qsusb.devices["@000ba0"] = QSDev(data={"id": "@000ba0", "type": "rel"})
    qsusb.timeout = 1
    qsusb.listen(cb)
    await asyncio.sleep(0.5)
    qsusb.stop()

    assert cb.call_args_list == [call(p) for p in packets]


async def test_version(qsusb: QSUsb, mock_aioresponse: aioresponses):
    """Test Qsusb version."""
    mock_aioresponse.get("http://localhost:2020/&version?", body="1.0.0")
    version = await qsusb.version()
    assert version == "1.0.0"
