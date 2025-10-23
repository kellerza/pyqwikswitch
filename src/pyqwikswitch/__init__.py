"""QwikSwitch USB Modem library for Python.

See: http://www.qwikswitch.co.za/qs-usb.php

Currently supports relays, buttons and LED dimmers

Source: http://www.github.com/kellerza/pyqwikswitch
"""

from pyqwikswitch.qsusb import QSUsb, qsusb_factory
from pyqwikswitch.qwikswitch import QSDev, QSDevices

__all__ = ["QSDev", "QSDevices", "QSUsb", "qsusb_factory"]
