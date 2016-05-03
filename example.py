#!/usr/bin/env python
"""
Basic usage example and testing of pyqwikswitch
"""

from time import sleep
import pyqwikswitch

TEST_URL = 'http://localhost:2020'
TEST_ID = '@0ac2f0'


def main():
    """QSUsb class quick test"""

    print('Execute a basic test on {}\nserver: {}\n'.format(TEST_ID, TEST_URL))

    def print_cmd(item):
        """prit a item"""
        print('&listen [{}, {}={}]'.format(
            item.get('cmd', ''),
            item.get('id', ''),
            item.get('data', '')))

    qsusb = pyqwikswitch.QSUsb(TEST_URL)

    qsusb.listen(print_cmd, timeout=5)
    print("Started listening")
    print("\n\n.devices()\n")
    print(qsusb.devices())
    for value in (100, 50, 0):
        sleep(3)
        print("\nSet {} = {}".format(TEST_ID, value))
        qsusb.set(TEST_ID, value)
        print(qsusb.devices(TEST_ID))
    sleep(20)
    print("Stopped listening")
    qsusb.stop()  # Close all threads

if __name__ == "__main__":
    main()
