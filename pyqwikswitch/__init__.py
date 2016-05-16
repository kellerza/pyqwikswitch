"""
  QwikSwitch USB Modem library for Python

  See: http://www.qwikswitch.co.za/qs-usb.php

  Currently supports relays, buttons and LED dimmers

    Source: http://www.github.com/kellerza/pyqwikswitch
"""

from queue import Queue
import threading
from time import sleep
import math
import requests

CMD = 'cmd'
CMD_BUTTONS = ['TOGGLE', 'SCENE EXE', 'LEVEL']
"""
Commands ['cmd'] strings used by QS buttons
  Toggle - Normal button
  Scene exe - execute scene
  Level - switch all lights off
"""  # pylint: disable=W0105


# pylint: disable=too-many-instance-attributes
class QSUsb(object):
    """
    Class to interface the QwikSwitch USB modem
    """
    def __init__(self, url, logger=None, dim_adj=1.4):
        """Init the Qwikswitch class
           url: URL for the QS class (e.g. http://localhost:8080)
           dim_adj: adjust dimmers values exponentially
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
        """Internal log errors"""
        try:
            self._logger.error(msg)
        except Exception:  # pylint: disable=broad-except
            print('ERROR: ' + msg)

    def _callback_thread(self):
        """Process callbacks from the queue populated by &listen"""
        while self._running:
            # Retrieve next cmd, or block
            packet = self._queue.get(True)
            if isinstance(packet, dict) and CMD in packet:
                try:
                    self.callback(packet)
                except Exception as err:  # pylint: disable=broad-except
                    self._log("Exception in qwikswitch callback\nType: " +
                              str(type(err)) + "\nMessage: " + str(err))
            self._queue.task_done()

    def _listen_thread(self):
        """The main &listen loop"""
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
                    self._queue.put({CMD: 'update'})
                else:  # "Connection refused" QSUSB down
                    self._log(str(err))
                    sleep(60)
            except Exception as err:  # pylint: disable=broad-except
                self._log(str(type(err)) + str(err))
                sleep(5)

        self._queue.put({})  # empty item to ensure callback thread shuts down

    def stop(self):
        """Stop listening"""
        self._running = False

    def callback(self, item):
        """ callback supplied to listen() or can be overridden"""
        if self._callback is not None:
            self._callback(item)

    def listen(self, callback=None, timeout=(5, 300)):
        """Start the &listen long poll and return immediately"""
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

    def set(self, qs_id, value, _repeat=3):
        """Push state to QSUSB, retry up to 3 times"""
        if _repeat == 3:
            value = self._encode_value(qs_id, value)

        set_result = requests.get(self._url + qs_id + '=' + str(value))
        if set_result.status_code == 200:
            set_result = set_result.json()
            if set_result.get('data', 'NO REPLY') != 'NO REPLY':
                return set_result['data']
            elif _repeat > 1:
                sleep(0.01*(5-_repeat))
                return self.set(qs_id, value, _repeat-1)
        return False

    def _encode_value(self, qs_id, value):
        """Encode value to be passed to QSUSB"""
        qstype = self._types.get(qs_id, '')

        if qstype == 'dim':
            return 100 if value > 90 else \
                   round(math.pow(value, 1/self._dim_adj))
        elif qstype == 'rel':
            return 100 if value > 0 else 0
        return value

    def _decode_value(self, item):
        """Decode the ['val'] value from QSUSB into a 0-100 ['value']

        Used by .devices()
        """
        val = item['val']
        if val == "":
            item['value'] = -1
            return item
        self._types[item['id']] = item['type']
        if item['type'] == 'rel':
            val = 0 if val == 'OFF' else \
                  100 if val == 'ON' else -1
            item['value'] = val
        elif item['type'] == 'dim':
            try:
                val = (120-int(val[-2:], 16))/1.2
                # Adjust dimmer exponentially to get a smoother effect
                val = round(math.pow(val, self._dim_adj))
                if val > 100:
                    val = 100
            except ValueError:
                self._log('''Unable to convert hex value in QS
                    dimmer data {}: {}'''.format(
                        item.get('name', ''),
                        val[-2:]))
                val = -1
            item['value'] = val
        return item

    def devices(self, qs_id=None):
        """
        Retrieve a list of devices and values,
        or limit to a specific device ID
        """
        try:
            rest = requests.get(self._url + '&device')
            if rest.status_code == 200:
                devices = rest.json()
                if qs_id is None:
                    return [self._decode_value(i) for i in devices]
                else:
                    device = next((x for x in devices if x['id'] == qs_id), {})
                    return self._decode_value(device)
        except requests.exceptions.ConnectionError as conn_err:
            self._log('Could not connect: '+str(conn_err))
        except TypeError:
            pass
        return False
