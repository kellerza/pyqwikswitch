"""QwikSwitch USB Modem threaded library for Python."""

import logging
from queue import Queue
import threading
from time import sleep

import requests

from .qwikswitch import (
    QSDevices, QS_CMD, CMD_UPDATE,
    URL_DEVICES, URL_LISTEN, URL_SET, URL_VERSION)  # pylint: disable=W0614

_LOGGER = logging.getLogger(__name__)


# pylint: disable=too-many-instance-attributes
class QSUsb(object):
    """Class to interface the QwikSwitch USB modem."""

    def __init__(self, url, dim_adj, callback_value_changed):
        """Init the Qwikswitch class.

        url: URL for the QS class (e.g. http://localhost:8080)
        dim_adj: adjust dimmers values exponentially.
        callback_qs_to_value: set the value upon qs change
        """
        self._url = url.strip('/')
        self._running = False
        self.devices = QSDevices(
            callback_value_changed, self._callback_set_qs_value, dim_adj)
        self._timeout = 300
        self._queue = None
        self._callback_listen = None
        self._types = {}
        self._lock = threading.Lock()

        # Update internal state
        if not self.update_from_devices():
            raise ValueError('Cannot connect to the QSUSB hub ' + url)

    def _thread_worker(self):
        """Process callbacks from the queue populated by &listen."""
        while self._running:
            # Retrieve next cmd, or block
            packet = self._queue.get(True)
            if isinstance(packet, dict) and QS_CMD in packet:
                try:
                    self._callback_listen(packet)
                except Exception as err:  # pylint: disable=broad-except
                    _LOGGER.error("Exception in callback\nType: %s: %s",
                                  type(err), err)
            self._queue.task_done()

    def _thread_listen(self):
        """The main &listen loop."""
        while self._running:
            try:
                rest = requests.get(URL_LISTEN.format(self._url),
                                    timeout=self._timeout)
                if rest.status_code == 200:
                    self._queue.put(rest.json())
                else:
                    _LOGGER.error('QSUSB response code %s', rest.status_code)
                    sleep(30)

            # Received for "Read timed out" and "Connection refused"
            except requests.exceptions.ConnectionError as err:
                if str(err).find('timed') > 0:  # "Read timedout" update
                    self._queue.put({QS_CMD: CMD_UPDATE})
                else:  # "Connection refused" QSUSB down
                    _LOGGER.error(str(err))
                    sleep(60)
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.error(str(type(err)) + str(err))
                sleep(5)

        self._queue.put({})  # empty item to ensure callback thread shuts down

    def stop(self):
        """Stop listening."""
        self._running = False

    def version(self):
        """Get the QS Mobile version."""
        # requests.get destroys the ?
        import urllib
        with urllib.request.urlopen(URL_VERSION.format(self._url)) as response:
            return response.read().decode('utf-8')
        return False

    def listen(self, callback=None, timeout=(5, 300)):
        """Start the &listen long poll and return immediately."""
        if self._running:
            return False
        # if self.devices() is False:
        #    return False
        self._queue = Queue()
        self._running = True
        self._timeout = timeout
        self._callback_listen = callback
        threading.Thread(target=self._thread_listen, args=()).start()
        threading.Thread(target=self._thread_worker, args=()).start()
        return True

    def _callback_set_qs_value(self, key, val, success):
        """Push state to QSUSB, retry with backoff."""
        set_url = URL_SET.format(self._url, key, val)
        with self._lock:
            for _repeat in range(1, 6):
                set_result = requests.get(set_url)
                if set_result.status_code == 200:
                    set_result = set_result.json()
                    if set_result.get('data', 'NO REPLY') != 'NO REPLY':
                        # self.devices._set_qs_value(key, set_result['data'])
                        success()
                        return True
                sleep(0.01*_repeat)
        _LOGGER.error("Unable to set %s", set_url)
        return False

    def update_from_devices(self):
        """Retrieve a list of &devices and values."""
        # _LOGGER.warning("update from devices")
        try:
            rest = requests.get(URL_DEVICES.format(self._url))
            if rest.status_code != 200:
                _LOGGER.error("Devices returned %s", rest.status_code)
                return False
            self.devices.update_devices(rest.json())
            return True
        except requests.exceptions.ConnectionError as conn_err:
            _LOGGER.error("Could not connect: %s", conn_err)
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error(err)
