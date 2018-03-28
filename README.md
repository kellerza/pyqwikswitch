# pyqwikswitch library
QwikSwitch USB Modem library for Python 3

  See http://www.qwikswitch.co.za for more information on the Qwikswitch devices

  Currently supports relays, buttons and LED dimmers

##  QSUsb class

* Get a list of all devices & values. *(http://localhost:2020/&device)*

  `QSUsb.devices()`

  ```
  [{"id": "@0c26e0","name": "buitelig","type": "rel","val": "ON",
        "time": "1460146507","rssi": "45%"},
    .....]
  ```

* Long poll *(http://localhost:8080/&listen)* for device changes and
    button presses. This is non-blocking and should be stopped manually (`.stop()`)

  `QSUsb.listen(callback)`


* Set a specific device according to ID. (dim 5%) or 100 (on) *(http://localhost:8080/@0ac2f0=5)*

  `QSUsb.set(id, value)`

  Dimmers values can be adjusted to get a more linear behaviour by setting `dim_adj` between 1 - 2


## Example usage

See [example.py](./example.py) for a basic usage and tests
