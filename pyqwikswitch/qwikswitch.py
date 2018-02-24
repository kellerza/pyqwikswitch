"""QwikSwitch USB Modem library for Python.

See: http://www.qwikswitch.co.za/qs-usb.php

Currently supports relays, buttons and LED dimmers

Source: http://www.github.com/kellerza/pyqwikswitch
"""

import logging
import math
from enum import Enum

_LOGGER = logging.getLogger(__name__)

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

QSVAL = 'qs_val'
QSDATA = 'data'

CMD_UPDATE = 'update'

URL_LISTEN = "{}/&listen"
URL_VERSION = "{}/&version?"
URL_SET = "{}/{}={}"
URL_DEVICES = "{}/&device"


class QSType(Enum):
    """Supported QSUSB types."""

    relay = 1  # rel
    dimmer = 2  # dim
    unknown = 9


QS_TYPES = {'rel': QSType.relay,
            'dim': QSType.dimmer}
_MAX = 255


# pylint: disable=too-many-return-statements, too-many-branches
def _legacy_status(stat):
    """Legacy status method from the 'qsmobile.js' library.

    Pass in the 'val' from &devices or the
    'data' received after calling a specific ID.
    """
    # 2d0c00002a0000
    if stat[:2] == '30' or stat[:2] == '47':  # RX1 CT
        ooo = stat[4:5]
        # console.log("legstat. " + o);
        if ooo == '0':
            return 0
        if ooo == '8':
            return 100
    if stat == '7e':
        return 0
    if stat == '7f':
        return 100
    if len(stat) == 6:  # old
        try:
            val = int(stat[4:], 16)
        except ValueError:
            val = 0
        hwt = stat[:2]
        if hwt == '01':  # old dim
            return round(((125 - val) / 125) * 100)
        if hwt == '02':  # old rel
            return 100 if val == 127 else 0
        if hwt == '28':  # LED DIM
            if stat[2:4] == '01':
                if stat[4:] == '78':
                    return 0
            return round(((120 - val) / 120) * 100)

    # Additional decodes not part of qsmobile.js
    if stat.upper().find('ON') >= 0:  # Relay
        return 100
    if (not stat) or stat.upper().find('OFF') >= 0:
        return 0
    if stat.endswith('%'):  # New style dimmers
        if stat[:-1].isdigit:
            return int(stat[:-1])
    print('val="{}" used a -1 fallback in legacy_status'.format(stat))
    return -1  # fallback to return an int
    # return stat


def decode_qwikcord(val):
    """Extract the qwikcord current measurements from val (CTavg, CTsum)."""
    if len(val) != 16:
        return None
    return (int(val[6:12], 16), int(val[12:], 16))


_KEYS = [QS_TYPE, QS_VALUE, QSDATA]


class QSDevices:
    """Represent the devices from QS Mobile."""
    _data = {}

    def __init__(self, cb_value_changed, cb_set_qsvalue, dim_adj=1):
        """Initialize."""
        self.dim_adj = dim_adj
        self._cb_value_changed = cb_value_changed
        self._cb_set_qsvalue = cb_set_qsvalue

    def __iter__(self):
        """Iterate over the devices _data."""
        for key, val in self._data.items():
            yield (key, dict(zip(_KEYS, val)))

    def __getitem__(self, key):
        """Retrieve a device."""
        if isinstance(key, str):
            val = self._data[key]
            return dict(zip(_KEYS, val))

        if not isinstance(key, tuple) or len(key) != 2:
            raise IndexError('Index must be an ID or tuple of length 2: {}'
                             .format(key))
        try:
            val = self._data[key[0]]
            if key[1] in _KEYS:
                return val[_KEYS.index(key[1])]
            return val[key[1]]
        except KeyError:
            raise KeyError("Key {} not found/invalid".format(key))

    def __len__(self):
        """Return the length."""
        return len(self._data)

    def set_value(self, key, new):
        # Set value & encode new to be passed to QSUSB
        """Set a value."""
        try:
            qsd = self._data[key]
        except KeyError:
            raise KeyError("Device {} not found".format(key))
        if new < 0:
            new = 0
        if new == qsd[1]:
            return

        if qsd[0] == QSType.dimmer:
            new = _MAX if new > (_MAX*.9) else new
        else:  # QSType.relay and any other
            new = _MAX if new > 0 else 0

        def success():
            """Success closure to update value."""
            self._data[key][1] = new  # qsd[1] = new
            _LOGGER.debug("set success %s", new)
            self._cb_value_changed(self, key, new)

        newqs = round(math.pow(round(new/_MAX*100), 1/self.dim_adj))
        _LOGGER.debug("%s hass=%s --> %s", key, new, newqs)
        self._cb_set_qsvalue(key, newqs, success)

    def update_devices(self, devices):
        """Update values from response of URL_DEVICES, callback if changed."""
        for dev in devices:
            try:
                _id = dev[QS_ID]
            except KeyError:
                _LOGGER.debug("Device without ID: %s", dev)
                continue
            if _id not in self._data:
                self._data[_id] = [QS_TYPES.get(dev[QS_TYPE],
                                                QSType.unknown), -5, dev]

            qsd = self._data[_id]
            qsd[2] = dev
            # Decode value from QSUSB
            newqs = _legacy_status(dev[QS_VALUE])
            if qsd[0] == QSType.dimmer:
                # Adjust dimmer exponentially to get a smoother effect
                newqs = min(round(math.pow(newqs, self.dim_adj)), 100)
            newin = round(newqs*_MAX/100)
            if abs(qsd[1]-newin) > 1:
                _LOGGER.debug("%s qs=%s  -->  %s", _id, newqs, newin)
                qsd[1] = newin
                self._cb_value_changed(self, _id, newin)
