"""QwikSwitch USB Modem async library for Python."""

import asyncio
import logging
from collections.abc import Callable
from typing import Any

import aiohttp
import attrs

from .qwikswitch import (
    QS_CMD,
    URL_DEVICES,
    URL_LISTEN,
    URL_SET,
    URL_VERSION,
    QSDevices,
)

_LOGGER = logging.getLogger(__name__)


async def qsusb_factory(
    url: str,
    dim_adj: float,
    callback_value_changed: Callable[[str, int | float], None],
    session: aiohttp.ClientSession,
) -> "QSUsb":
    """Create the QSUsb instance."""
    client = QSUsb(
        url=url,
        session=session,
        loop=asyncio.get_running_loop(),
        devices=QSDevices(
            cb_value_changed=callback_value_changed,
            cb_set_qsvalue=lambda qsid, val, success_cb: None,
            dim_adj=dim_adj,
        ),
    )
    return client


@attrs.define(slots=True)
class QSUsb:
    """Class to interface the QwikSwitch USB modem."""

    url: str
    session: aiohttp.ClientSession = attrs.field(repr=False)
    devices: QSDevices = attrs.field(repr=False)
    loop: asyncio.AbstractEventLoop = attrs.field(repr=False)

    running: bool = attrs.field(default=False, init=False)
    timeout: int = attrs.field(default=300)
    tasks: dict[str, asyncio.Task] = attrs.field(factory=dict, repr=False)

    def __attrs_post_init__(self) -> None:
        """Post init to set up devices."""
        self.url = self.url.strip("/")
        self.devices.cb_set_qsvalue = self.set_qs_value

    async def get_json(
        self,
        url: str,
        timeout: int = 30,  # noqa: ASYNC109
        exceptions: bool = False,
    ) -> dict[str, Any] | None:
        """Get URL and parse JSON from text."""
        _LOGGER.debug("GET %s", url)
        try:
            async with asyncio.timeout(timeout):
                async with self.session.get(url) as res:
                    if res.status != 200:
                        _LOGGER.error("QSUSB returned %s [%s]", res.status, url)
                        return None
                    _LOGGER.debug("QSUSB response %s", res.status)
                    return await res.json()
        except TimeoutError as exc:
            if exceptions:
                raise exc
            _LOGGER.error("Timeout %s", url)
        except Exception as exc:
            if exceptions:
                raise exc
            _LOGGER.error(exc)
        return None

    def stop(self) -> None:
        """Stop listening."""
        self.running = False
        for task in list(self.tasks.values()):
            task.cancel()

    async def version(self) -> str:
        """Get the QS Mobile version."""
        url = URL_VERSION.format(self.url)
        async with asyncio.timeout(30):
            async with self.session.get(url) as res:
                if res.status != 200:
                    _LOGGER.warning("QSUSB returned %s [%s]", res.status, url)
                    return ""
                return await res.text()

    def listen(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Start the &listen long poll and return immediately."""
        self.running = True
        self.tasks["listen"] = self.loop.create_task(self.listen_loop(callback))

    async def listen_loop(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Listen loop."""
        try:
            while self.running:
                try:
                    packet = await self.get_json(
                        URL_LISTEN.format(self.url),
                        timeout=self.timeout,
                        exceptions=True,
                    )
                except TimeoutError:
                    continue
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    _LOGGER.error("Listen: Exception getting packet: %s", exc)
                    await asyncio.sleep(30)
                    continue

                if isinstance(packet, dict) and QS_CMD in packet:
                    _LOGGER.debug("callback( %s )", packet)
                    try:
                        callback(packet)
                    except asyncio.CancelledError:
                        raise
                    except Exception as err:
                        _LOGGER.error(
                            "Listen: Exception in callback: Type: %s: %s",
                            type(err),
                            err,
                        )
                else:
                    _LOGGER.warning("Listen: Ignoring unknown packet? %s", packet)
        except asyncio.CancelledError:
            _LOGGER.debug("Listen: Cancelled")
        finally:
            self.running = False

    def set_qs_value(
        self, qsid: str, val: float, success_cb: Callable[[], None]
    ) -> None:
        """Push state to QSUSB, retry with backoff."""
        self.loop.create_task(self.async_set_qs_value(qsid, val, success_cb))

    async def async_set_qs_value(
        self, qsid: str, val: float, success_cb: Callable[[], None] | None = None
    ) -> bool:
        """Push state to QSUSB, retry with backoff."""
        set_url = URL_SET.format(self.url, qsid, val)
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
        res = await self.get_json(URL_DEVICES.format(self.url))
        if isinstance(res, list):
            self.devices.update_devices(res)
            return True
        return False
