"""QwikSwitch USB Modem library for Python.

See: http://www.qwikswitch.co.za/qs-usb.php

Currently supports relays, buttons and LED dimmers

Source: http://www.github.com/kellerza/pyqwikswitch
"""
import logging
import math
from enum import Enum

import attr

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
    humidity_temperature = 3  # hum
    unknown = 9


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
    _LOGGER.debug("val='%s' used a -1 fallback in legacy_status", stat)
    return -1  # fallback to return an int
    # return stat


@attr.s(slots=True)
class QSDev():
    """A single QS device."""

    data = attr.ib(validator=attr.validators.instance_of(dict))
    qstype = attr.ib(init=False, validator=attr.validators.instance_of(QSType))
    value = attr.ib(
        default=-5, validator=attr.validators.instance_of((float, int)))

    def __attrs_post_init__(self):
        """Init."""
        # pylint: disable=no-member
        _types = {'rel': QSType.relay, 'dim': QSType.dimmer,
                  'hum': QSType.humidity_temperature}
        self.qstype = _types.get(self.data.get(QS_TYPE, ''), QSType.unknown)

    @property
    def name(self):
        """Return the name from the qsusb data."""
        # pylint: disable=unsubscriptable-object
        try:
            return self.data[QS_NAME]
        except IndexError:
            return self.data[QS_ID]

    @property
    def qsid(self):
        """Return the name from the qsusb data."""
        return self.data.get(QS_ID, '')  # pylint: disable=no-member

    @property
    def is_dimmer(self):
        """Return the name from the qsusb data."""
        return self.qstype == QSType.dimmer


class QSDevices(dict):
    """Represent the devices from QS Mobile."""

    def __init__(self, cb_value_changed, cb_set_qsvalue, dim_adj=1):
        """Initialize."""
        self.dim_adj = dim_adj
        self._cb_value_changed = cb_value_changed
        self._cb_set_qsvalue = cb_set_qsvalue
        super().__init__()

    def set_value(self, qsid, new):
        # Set value & encode new to be passed to QSUSB
        """Set a value."""
        try:
            dev = self[qsid]
        except KeyError:
            raise KeyError("Device {} not found".format(qsid))
        if new < 0:
            new = 0
        if new == dev.value:
            return

        if dev.is_dimmer:
            new = _MAX if new > (_MAX * .9) else new
        else:  # QSType.relay and any other
            new = _MAX if new > 0 else 0

        def success():
            """Success closure to update value."""
            self[qsid].value = new
            _LOGGER.debug("set success %s=%s", qsid, new)
            self._cb_value_changed(self, qsid, new)

        newqs = round(math.pow(round(new / _MAX * 100), 1 / self.dim_adj))
        _LOGGER.debug("%s hass=%s --> %s", qsid, new, newqs)
        self._cb_set_qsvalue(qsid, newqs, success)

    def update_devices(self, devices):
        """Update values from response of URL_DEVICES, callback if changed."""
        for qspacket in devices:
            try:
                qsid = qspacket[QS_ID]
            except KeyError:
                _LOGGER.debug("Device without ID: %s", qspacket)
                continue

            if qsid not in self:
                self[qsid] = QSDev(data=qspacket)

            dev = self[qsid]
            dev.data = qspacket
            # Decode value from QSUSB
            newqs = _legacy_status(qspacket[QS_VALUE])
            if dev.is_dimmer:
                # Adjust dimmer exponentially to get a smoother effect
                newqs = min(round(math.pow(newqs, self.dim_adj)), 100)
            newin = round(newqs * _MAX / 100)
            if abs(dev.value - newin) > 1:  # Significant change
                _LOGGER.debug("%s qs=%s  -->  %s", qsid, newqs, newin)
                dev.value = newin
                self._cb_value_changed(self, qsid, newin)


def decode_qwikcord(packet, channel=1):
    """Extract the qwikcord current measurements from val (CTavg, CTsum)."""
    val = str(packet.get('val', ''))
    if len(val) != 16:
        return None
    if channel == 1:
        return int(val[6:12], 16)  # CTavg
    return int(val[12:], 16)  # CTsum


def decode_door(packet, channel=1):
    """Decode a door sensor."""
    val = str(packet.get(QSDATA, ''))
    if len(val) == 6 and val.startswith('46') and channel == 1:
        return val[-1] == '0'
    return None


# byte 0:
#     4e = imod
#     46 = Door sensor
# byte 1: firmware
# byte 2:  bit values
#     00/64: Door open / Close
#     17/xx: All open / Channels 1-4 at 0004 0321
# byte 3: last change (imod)

def decode_imod(packet, channel=1):
    """Decode an 4 channel imod. May support 6 channels."""
    val = str(packet.get(QSDATA, ''))
    if len(val) == 8 and val.startswith('4e'):
        try:
            _map = ((5, 1), (5, 2), (5, 4), (4, 1), (5, 1), (5, 2))[
                channel - 1]
            return (int(val[_map[0]], 16) & _map[1]) == 0
        except IndexError:
            return None
    return None


# byte 0:  0f = pir
# byte 1:  firmware
# byte 2 and 3:  number of seconds (in hex) that the PIR sends
#                until a device should react.

def decode_pir(packet, channel=1):
    """Decode a PIR."""
    val = str(packet.get(QSDATA, ''))
    if len(val) == 8 and val.startswith('0f') and channel == 1:
        return int(val[-4:], 16) > 0
    return None


# byte 0:  34 = temperature / humidity
# byte 1:  firmware
# byte 2-3:  humidity
# byte 4-5:  temperature

def decode_temperature(packet, channel=1):
    """Decode the temperature."""
    val = str(packet.get(QSDATA, ''))
    if len(val) == 12 and val.startswith('34') and channel == 1:
        temperature = int(val[-4:], 16)
        return round(float((-46.85 + (175.72 * (temperature / pow(2, 16))))))
    return None


def decode_humidity(packet, channel=1):
    """Decode the humidity."""
    val = str(packet.get(QSDATA, ''))
    if len(val) == 12 and val.startswith('34') and channel == 1:
        humidity = int(val[4:-4], 16)
        return round(float(-6 + (125 * (humidity / pow(2, 16)))))
    return None


SENSORS = {
    'imod': (decode_imod, bool),
    'door': (decode_door, bool),
    'pir': (decode_pir, bool),
    'temperature': (decode_temperature, '°C'),
    'humidity': (decode_humidity, '%'),
    'qwikcord': (decode_qwikcord, 'A/s'),
}
