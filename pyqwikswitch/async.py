"""QwikSwitch USB Modem async library for Python."""

import asyncio
import logging

import async_timeout

from .qwikswitch import (
    QSDevices, QS_CMD, CMD_UPDATE,
    URL_DEVICES, URL_LISTEN, URL_SET, URL_VERSION)  # pylint: disable=W0614

_LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes
class QSUsb(object):
    """Class to interface the QwikSwitch USB modem."""

    def __init__(self, url, dim_adj, callback_value_changed, loop):
        """Init the Qwikswitch class.

        url: URL for the QS class (e.g. http://localhost:8080)
        dim_adj: adjust dimmers values exponentially.
        callback_qs_to_value: set the value upon qs change
        """
        self._url = url.strip('/')
        self.loop = loop
        self._running = False
        self.devices = QSDevices(
            callback_value_changed, self._callback_set_qs_value, dim_adj)
        self._timeout = 300
        self._types = {}

    def stop(self):
        """Stop listening."""
        self._running = False

    @asyncio.coroutine
    def version(self):
        """Get the QS Mobile version."""
        _LOGGER.error(URL_VERSION)
        raise NotImplementedError

    def listen(self, callback=None, timeout=(5, 300)):
        """Start the &listen long poll and return immediately."""
        self._running = True
        self.loop.create_task(self._async_listen(callback, timeout))

    @asyncio.coroutine
    def _async_listen(self, callback=None, timeout=(5, 300)):
        """Listen loop."""
        while self._running:
            try:
                with async_timeout.timeout(30):
                    res = yield from self._aio_session.get(
                        URL_LISTEN.format(self._url))
            except Exception:
                pass

            if res.status_code != 200:
                _LOGGER('QSUSB response code ' + str(res.status_code))
                yield from asyncio.sleep(30)

            packet = (yield from res.json())
            if isinstance(packet, dict) and QS_CMD in packet:
                try:
                    self._callback_listen(packet)
                except Exception as err:  # pylint: disable=broad-except
                    _LOGGER("Exception in qwikswitch callback\nType: %s: %s",
                            type(err), err)

    def _callback_set_qs_value(self, key, val, success):
        """Push state to QSUSB, retry with backoff."""
        self.loop.create_task(_async_callback_set_qs_value(key, val, success))

    @asyncio.coroutine
    def _async_callback_set_qs_value(self, key, val, success):
        set_url = URL_SET.format(self._url, key, val)
        for _repeat in range(1, 6):
            res = yield from self._aio_session.get(set_url)
            if res.status_code == 200:
                set_result = yield from res.json()
                if set_result.get('data', 'NO REPLY') != 'NO REPLY':
                    success()
                    return
            yield from asyncio.sleep(0.01*_repeat)
        _LOGGER("Unable to set {}".format(set_url))

    @asyncio.coroutine
    def update_from_devices(self):
        """Retrieve a list of &devices and values."""
        try:
            with async_timeout.timeout(3):
                res = yield from self._aio_session.get(
                    URL_DEVICES.format(self._url))
                if res.status_code != 200:
                    return False
                json = (yield from res.json())
        except asyncio.TimeoutError as err:
            _LOGGER("Could not connect: {}".format(err))
        self.devices.update_devices(json)
