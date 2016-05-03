#!/usr/bin/env python
"""
Basic usage example and testing of pyqwikswitch
"""

from time import sleep
import pyqwikswitch

TEST_URL = 'http://localhost:2020'
TEST_DIM_ID = '@0ac2f0'
TEST_RELAY_ID = '@0c2700'


def main():
    """QSUsb class quick test"""

    print('Execute a basic test on server: {}\n'.format(TEST_URL))

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
    print("\n")
    
    for qsid in (TEST_RELAY_ID, TEST_DIM_ID):
        for value in (100, 50, 0):
            sleep(3)
            print("\nSet {} = {}".format(qsid, value))
            qsusb.set(qsid, value)
            print(qsusb.devices(qsid))
        sleep(2)
    print("\n\n.Listening for 20 seconds (test buttons now)\n")
    sleep(20)    
    print("Stopped listening")
    qsusb.stop()  # Close all threads

if __name__ == "__main__":
    main()
