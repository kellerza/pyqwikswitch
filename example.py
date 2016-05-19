#!/usr/bin/env python
"""Basic usage example and testing of pyqwikswitch. """

from time import sleep
import pyqwikswitch

TEST_URL = 'http://127.0.0.1:2020'
TEST_IDS = ['@000001','@0c2700', '@0ac2f0']


def main():
    """QSUsb class quick test."""
    print('Execute a basic test on server: {}\n'.format(TEST_URL))
    url = input('Enter new URL of [Enter] for default: ')
    if len(url) == 0:
        url = TEST_URL

    def print_callback(item):
        """prit an item callback."""
        print('&listen [{}, {}={}]'.format(
            item.get('cmd', ''),
            item.get('id', ''),
            item.get('data', '')))

    qsusb = pyqwikswitch.QSUsb(url)

    qsusb.listen(print_callback, timeout=5)
    print("Started listening")
    devs = qsusb.devices()
    print("\n\n.devices()\n[\n")
    for dev in devs:
        print(str(dev)+'\n')
    print("]\n")

    for qsid in TEST_IDS:
        for value in (100, 50, 0):
            sleep(3)
            print("\nSet {} = {}".format(qsid, value))
            val = qsusb.set(qsid, value)
            print("   --> result: {}".format(val))
            print(qsusb.devices(qsid))
        sleep(2)
    print("\n\nListening for 20 seconds (test buttons now)\n")
    sleep(20)
    print("Stopped listening")
    qsusb.stop()  # Close all threads

if __name__ == "__main__":
    main()
