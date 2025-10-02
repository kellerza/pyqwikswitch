"""QwikSwitch USB Modem async library for Python."""

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

import aiohttp

from .qwikswitch import (
    QS_CMD,
    URL_DEVICES,
    URL_LISTEN,
    URL_SET,
    URL_VERSION,
    QSDevices,
)

_LOGGER = logging.getLogger(__name__)


class QSUsb:
    """Class to interface the QwikSwitch USB modem."""

    def __init__(
        self,
        url: str,
        dim_adj: float,
        callback_value_changed: Callable[[str, int | float], None],
        session: aiohttp.ClientSession,
    ):
        """Init the Qwikswitch class.

        url: URL for the QS class (e.g. http://localhost:8080)
        dim_adj: adjust dimmers values exponentially.
        callback_qs_to_value: set the value upon qs change
        """
        _LOGGER.debug("init %s", url)
        self._url = url.strip("/")
        self.loop = session.loop
        self._running = False
        self.devices = QSDevices(
            cb_value_changed=callback_value_changed,
            cb_set_qsvalue=self.set_qs_value,
            dim_adj=dim_adj,
        )
        self._timeout = 300
        # self._types = {}
        self._aio_session = session
        self._sleep_task: asyncio.Task | None = None

    async def get_text(
        self,
        url: str,
        timeout: int = 30,  # noqa: ASYNC109
        exceptions: bool = False,
    ) -> str | None:
        """Get URL and parse JSON from text."""
        try:
            async with asyncio.timeout(timeout):
                res = await self._aio_session.get(url)
                if res.status != 200:
                    _LOGGER.error("QSUSB returned %s [%s]", res.status, url)
                    return None
                return await res.text()
        except (TimeoutError, aiohttp.ClientError) as exc:
            if exceptions:
                raise exc
            return None

    async def get_json(
        self,
        url: str,
        timeout: int = 30,  # noqa: ASYNC109
        exceptions: bool = False,
    ) -> dict[str, Any] | None:
        """Get URL and parse JSON from text."""
        res_text = (
            await self.get_text(url, timeout=timeout, exceptions=exceptions) or ""
        )
        try:
            return json.loads(res_text)
        except json.decoder.JSONDecodeError:
            _LOGGER.error("Could not decode %s [%s]", res_text, url)
        return None

    def stop(self) -> None:
        """Stop listening."""
        self._running = False
        if self._sleep_task:
            self._sleep_task.cancel()
            self._sleep_task = None

    async def version(self) -> str:
        """Get the QS Mobile version."""
        return await self.get_text(URL_VERSION.format(self._url)) or ""

    def listen(self, callback=None) -> None:
        """Start the &listen long poll and return immediately."""
        self._running = True
        self.loop.create_task(self._async_listen(callback))

    async def _async_listen(self, callback=None) -> None:
        """Listen loop."""
        while True:
            if not self._running:
                return

            try:
                packet = await self.get_json(
                    URL_LISTEN.format(self._url), timeout=30, exceptions=True
                )
            except TimeoutError:
                continue
            except aiohttp.ClientError as exc:
                _LOGGER.warning("ClientError: %s", exc)
                self._sleep_task = self.loop.create_task(asyncio.sleep(30))
                try:
                    await self._sleep_task
                except asyncio.CancelledError:
                    pass
                self._sleep_task = None
                continue

            if isinstance(packet, dict) and QS_CMD in packet:
                _LOGGER.debug("callback( %s )", packet)
                try:
                    if callback:
                        callback(packet)
                except Exception as err:
                    _LOGGER.error("Exception in callback\nType: %s: %s", type(err), err)
            else:
                _LOGGER.debug("unknown packet? %s", packet)

    def set_qs_value(
        self, qsid: str, val: float, success_cb: Callable[[], None]
    ) -> None:
        """Push state to QSUSB, retry with backoff."""
        self.loop.create_task(self.async_set_qs_value(qsid, val, success_cb))

    async def async_set_qs_value(
        self, qsid: str, val: float, success_cb: Callable[[], None] | None = None
    ) -> bool:
        """Push state to QSUSB, retry with backoff."""
        set_url = URL_SET.format(self._url, qsid, val)
        for _repeat in range(1, 6):
            set_result = await self.get_json(set_url, 2)
            if set_result and set_result.get("data", "NO REPLY") != "NO REPLY":
                if success_cb:
                    success_cb()
                return True
            await asyncio.sleep(0.01 * _repeat)
        _LOGGER.error("Unable to set %s", set_url)
        return False

    async def update_from_devices(self) -> bool:
        """Retrieve a list of &devices and values."""
        res = await self.get_json(URL_DEVICES.format(self._url))
        if isinstance(res, list):
            self.devices.update_devices(res)
            return True
        return False
