"""QwikSwitch USB Modem async library for Python."""
import asyncio
import json
import logging
import async_timeout

import aiohttp

from .qwikswitch import (
    QSDevices, QS_CMD, URL_DEVICES, URL_LISTEN, URL_SET, URL_VERSION
)  # apylint: disable=W0614

_LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes
class QSUsb(object):
    """Class to interface the QwikSwitch USB modem."""

    def __init__(self, url, dim_adj, callback_value_changed, session):
        """Init the Qwikswitch class.

        url: URL for the QS class (e.g. http://localhost:8080)
        dim_adj: adjust dimmers values exponentially.
        callback_qs_to_value: set the value upon qs change
        """
        _LOGGER.debug("init %s", url)
        self._url = url.strip('/')
        self.loop = session.loop
        self._running = False
        self.devices = QSDevices(
            callback_value_changed, self.set_qs_value, dim_adj)
        self._timeout = 300
        self._types = {}
        self._aio_session = session
        self._sleep_task = None

    async def get_json(self, url, timeout=30, astext=False):
        """Get URL and parse JOSN from text."""
        try:
            with async_timeout.timeout(timeout):
                res = await self._aio_session.get(url)
                if res.status != 200:
                    _LOGGER.error("QSUSB returned %s [%s]", res.status, url)
                    return None
                res_text = await res.text()
        except (aiohttp.client_exceptions.ClientConnectorError,
                asyncio.TimeoutError):
            return None

        if astext:
            return res_text

        try:
            return json.loads(res_text)
        except json.decoder.JSONDecodeError:
            if res_text.strip(" ") == "":
                return None
            _LOGGER.error("Could not decode %s [%s]", res_text, url)

    def stop(self):
        """Stop listening."""
        self._running = False
        if self._sleep_task:
            self._sleep_task.cancel()
            self._sleep_task = None

    def version(self):
        """Get the QS Mobile version."""
        return self.get_json(URL_VERSION.format(self._url), astext=True)

    def listen(self, callback=None):
        """Start the &listen long poll and return immediately."""
        self._running = True
        self.loop.create_task(self._async_listen(callback))

    async def _async_listen(self, callback=None):
        """Listen loop."""
        while True:
            if self._running:
                packet = await self.get_json(URL_LISTEN.format(self._url), 30)
            else:
                return

            if not packet:
                _LOGGER.debug('sleep start...')
                self._sleep_task = self.loop.create_task(asyncio.sleep(30))
                try:
                    await self._sleep_task
                    _LOGGER.debug('sleep done...')
                except asyncio.CancelledError:
                    _LOGGER.debug('sleep cancelled...')

                self._sleep_task = None
                continue

            if isinstance(packet, dict) and QS_CMD in packet:
                try:
                    callback(packet)
                except Exception as err:  # pylint: disable=broad-except
                    _LOGGER.error("Exception in callback\nType: %s: %s",
                                  type(err), err)

    def set_qs_value(self, qsid, val, success_cb):
        """Push state to QSUSB, retry with backoff."""
        self.loop.create_task(self.async_set_qs_value(qsid, val, success_cb))

    async def async_set_qs_value(self, qsid, val, success_cb=None):
        """Push state to QSUSB, retry with backoff."""
        set_url = URL_SET.format(self._url, qsid, val)
        for _repeat in range(1, 6):
            set_result = await self.get_json(set_url, 2)
            if set_result and set_result.get('data', 'NO REPLY') != 'NO REPLY':
                if success_cb:
                    success_cb()
                return True
            await asyncio.sleep(0.01*_repeat)
        _LOGGER.error("Unable to set %s", set_url)
        return False

    async def update_from_devices(self):
        """Retrieve a list of &devices and values."""
        res = await self.get_json(URL_DEVICES.format(self._url))
        if res:
            self.devices.update_devices(res)
            return True
        return False
