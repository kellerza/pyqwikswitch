# pyqwikswitch library [![codecov](https://codecov.io/gh/kellerza/pyqwikswitch/graph/badge.svg?token=aw8RRebC8L)](https://codecov.io/gh/kellerza/pyqwikswitch)

QwikSwitch USB Modem library for Python 3.
The library supports relays, buttons, LED dimmers and decoding of various [sensors](https://github.com/kellerza/pyqwikswitch/blob/main/pyqwikswitch/qwikswitch.py#L277)

See http://www.qwikswitch.co.za for more information on the Qwikswitch devices.

The library is used in the Home Assistant [QwikSwitch integration](https://www.home-assistant.io/integrations/qwikswitch/)

##  QSUsb class

* Get a list of all devices & values. *(http://localhost:2020/&device)*

  `QSUsb.devices()`

  ```
  [{"id": "@0c26e0","name": "Light 1","type": "rel","val": "ON",
        "time": "1460146507","rssi": "45%"},
    .....]
  ```

* Long poll *(http://localhost:8080/&listen)* for device changes and
    button presses. This is non-blocking and should be stopped manually (`.stop()`)

  `QSUsb.listen(callback)`


* Set a specific device according to ID. (dim 5%) or 100 (on) *(http://localhost:8080/@0ac2f0=5)*

  `QSUsb.set(id, value)`

  Dimmer values can be adjusted to get a more linear behavior by setting `dim_adj` between 1 - 2


## Example usage

See [example.py](./example.py) for a basic usage and tests though the synchronous interface
