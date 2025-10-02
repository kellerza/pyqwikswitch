"""Tests."""

from aiohttp import ClientSession

from pyqwikswitch.async_ import QSUsb


async def test_qsusb_init():
    """Test Qsusb."""
    async with ClientSession() as session:
        qsusb = QSUsb("http://localhost:2020", 1.0, lambda x, y: None, session)
        assert qsusb is not None
