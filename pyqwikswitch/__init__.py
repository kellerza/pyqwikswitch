"""QwikSwitch USB Modem library for Python.

See: http://www.qwikswitch.co.za/qs-usb.php

Currently supports relays, buttons and LED dimmers

Source: http://www.github.com/kellerza/pyqwikswitch
"""

from queue import Queue
import threading
from time import sleep
import math
from enum import Enum
import requests

QS_CMD = 'cmd'
CMD_BUTTONS = ['TOGGLE', 'SCENE EXE', 'LEVEL']
"""
Commands ['cmd'] strings used by QS buttons
  Toggle - Normal button
  Scene exe - execute scene
  Level - switch all lights off
"""  # pylint: disable=W0105

QS_ID = 'id'
QS_VALUE = 'val'
QS_TYPE = 'type'
QS_NAME = 'name'

PQS_VALUE = 'valP'
PQS_TYPE = 'typeP'
CMD_UPDATE = 'update'


class QSType(Enum):
    """Supported QSUSB types."""

    relay = 1  # rel
    dimmer = 2  # dim
    unknown = 9
QS_TYPES = {'rel': QSType.relay,
            'dim': QSType.dimmer}


# pylint: disable=too-many-instance-attributes
class QSUsb(object):
    """Class to interface the QwikSwitch USB modem."""

    def __init__(self, url, logger=None, dim_adj=1.4):
        """Init the Qwikswitch class.

        url: URL for the QS class (e.g. http://localhost:8080)
        dim_adj: adjust dimmers values exponentially.
        """
        self._url = url
        if not url.endswith('/'):
            self._url += '/'
        self._running = False
        self._logger = logger
        self._dim_adj = dim_adj
        self._timeout = 300
        self._queue = None
        self._callback = None
        self._types = {}
        if self.devices() is False:
            raise ValueError('Cannot connect to the QSUSB hub ' + url)

    def _log(self, msg):
        """Internal log errors."""
        try:
            self._logger.error(msg)
        except Exception:  # pylint: disable=broad-except
            print('ERROR: ' + msg)

    def _callback_thread(self):
        """Process callbacks from the queue populated by &listen."""
        while self._running:
            # Retrieve next cmd, or block
            packet = self._queue.get(True)
            if isinstance(packet, dict) and QS_CMD in packet:
                try:
                    self.callback(packet)
                except Exception as err:  # pylint: disable=broad-except
                    self._log("Exception in qwikswitch callback\nType: " +
                              str(type(err)) + "\nMessage: " + str(err))
            self._queue.task_done()

    def _listen_thread(self):
        """The main &listen loop."""
        while self._running:
            try:
                rest = requests.get(self._url + '&listen',
                                    timeout=self._timeout)
                if rest.status_code == 200:
                    self._queue.put(rest.json())
                else:
                    self._log('QSUSB response code ' + str(rest.status_code))
                    sleep(30)
            # Received for "Read timed out" and "Connection refused"
            except requests.exceptions.ConnectionError as err:
                if str(err).find('timed') > 0:  # "Read timedout" update
                    self._queue.put({QS_CMD: CMD_UPDATE})
                else:  # "Connection refused" QSUSB down
                    self._log(str(err))
                    sleep(60)
            except Exception as err:  # pylint: disable=broad-except
                self._log(str(type(err)) + str(err))
                sleep(5)

        self._queue.put({})  # empty item to ensure callback thread shuts down

    def stop(self):
        """Stop listening."""
        self._running = False

    def callback(self, item):
        """Callback supplied to listen() or can be overridden."""
        if self._callback is not None:
            self._callback(item)

    def listen(self, callback=None, timeout=(5, 300)):
        """Start the &listen long poll and return immediately."""
        if self._running:
            return False
        if self.devices() is False:
            return False
        self._queue = Queue()
        self._running = True
        self._timeout = timeout
        self._callback = callback
        threading.Thread(target=self._listen_thread, args=()).start()
        threading.Thread(target=self._callback_thread, args=()).start()
        return True

    def set(self, qs_id, value, _repeat=None):
        """Push state to QSUSB, retry with backoff."""
        if _repeat is None:
            _repeat = 5
            value = self._encode_value(qs_id, value)

        set_result = requests.get(self._url + qs_id + '=' + str(value))
        if set_result.status_code == 200:
            set_result = set_result.json()
            if set_result.get('data', 'NO REPLY') != 'NO REPLY':
                return self._decode_value(qs_id, set_result['data'])
            elif _repeat > 1:
                sleep(0.005*(6-_repeat))
                return self.set(qs_id, value, _repeat-1)
        return -1

    def _encode_value(self, qs_id, value):
        """Encode value to be passed to QSUSB."""
        qstype = self._types.get(qs_id, '')
        if value < 0:
            value = 0
        if qstype == QSType.dimmer:
            return 100 if value > 90 else \
                   round(math.pow(value, 1/self._dim_adj))
        elif qstype == QSType.relay:
            return 100 if value > 0 else 0
        return value

    def _decode_value(self, qs_id, qsval):
        """Encode value to be passed to QSUSB."""
        qstype = self._types.get(qs_id, '')
        if qstype == QSType.relay:
            return 0 if qsval == 'OFF' else \
                   100 if qsval == 'ON' else -1
        elif qstype == QSType.dimmer and len(qsval) > 2:
            try:
                val = (120-int(qsval[-2:], 16))/1.2
                # Adjust dimmer exponentially to get a smoother effect
                val = round(math.pow(val, self._dim_adj))
            except ValueError:
                self._log('''Unable to convert hex value in QS dimmer data
                          {}: {}'''.format(qs_id, val[-2:]))
                return -1
            else:
                return min(val, 100)
        return qsval

    def devices(self, qs_ids=None):
        """Retrieve a list of devices and values (optionally limit to ID).

        Optionally limit the result to a list of QS_IDs.
        This will add the decoded value in [PQS_VALUE] for each device.
        """
        try:
            rest = requests.get(self._url + '&device')
            if rest.status_code == 200:
                devices = rest.json()
                devices = [x for x in devices if QS_ID in x]  # Ensure ID
                if qs_ids is not None:  # filter on 'ids'
                    devices = [x for x in devices if x[QS_ID] in qs_ids]
                for dev in devices:
                    qs_id = dev[QS_ID]
                    if qs_id not in self._types:
                        self._types[qs_id] = QS_TYPES.get(dev[QS_TYPE],
                                                          QSType.unknown)
                    dev[PQS_TYPE] = self._types[qs_id]
                    dev[PQS_VALUE] = self._decode_value(qs_id, dev[QS_VALUE])
                return devices
        except requests.exceptions.ConnectionError as conn_err:
            self._log('Could not connect: '+str(conn_err))
        except TypeError:
            pass
        return False
