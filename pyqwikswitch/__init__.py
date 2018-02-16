"""QwikSwitch USB Modem library for Python.

See: http://www.qwikswitch.co.za/qs-usb.php

Currently supports relays, buttons and LED dimmers

Source: http://www.github.com/kellerza/pyqwikswitch
"""

from .qwikswitch import *  # pylint: disable=W0614

__all__ = ["async", "threaded"]
