#!/usr/bin/env python
"""Basic usage example and testing of pyqwikswitch."""

import json
from time import sleep

from pyqwikswitch.qwikswitch import (QS_ID, QS_VALUE, QSDevices, QSType,
                                     decode_qwikcord)
from pyqwikswitch.threaded import QSUsb


def print_bad_data(json_list):
    """Print error if ID invalid."""
    for dev in json_list:
        if QS_ID not in dev:
            print("**ERR NO ID:", dev)


def print_devices_change_callback(devices, key, new):
    """Print the reply from &devices() and highlight errors."""
    dev = devices[key]
    print('- ', new, ' ', dev)
    if dev['type'] == QSType.unknown:
        print(" ERR decoding")
    elif dev['value'] == -1:
        dev(" ERR decoding: -1?")
    qcord = decode_qwikcord(dev['data'][QS_VALUE])
    if qcord is not None:
        print(' qwikcord (CTAVG, CTsum) = ' + str(qcord))


def print_item_callback(item):
    """Print an item callback, used by &listen."""
    print('&listen [{}, {}={}]'.format(
        item.get('cmd', ''),
        item.get('id', ''),
        item.get('data', '')))


def test_devices_set(devices, ids):
    """Test the set method for ids passed in.

    In this example using --test_ids @id1,@id2.
    """
    for _id in ids:
        for value in (10, 9):
            sleep(3)
            print("\nSet {} = {}".format(_id, value))
            val = devices.set_value(_id, value)
            print("   --> result: {}".format(val))
            print(devices[_id])
        sleep(2)


def main():
    """Quick test for QSUsb class."""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', help='QSUSB URL [http://127.0.0.1:2020]',
                        default='http://127.0.0.1:2020')
    parser.add_argument('--file', help='a test file from /&devices')
    parser.add_argument('--test_ids', help='List of test IDs',
                        default='@0c2700,@0ac2f0')
    args = parser.parse_args()

    if args.file:
        with open(args.file) as data_file:
            data = json.load(data_file)
        qsusb = QSDevices(
            print_devices_change_callback, print_devices_change_callback)
        print_bad_data(data)
        qsusb.set_qs_values(data)
        return

    print('Execute a basic test on server: {}\n'.format(args.url))

    def qs_to_value(key, new):
        print(" --> New value: {}={}".format(key, new))

    qsusb = QSUsb(args.url, 1, qs_to_value)
    print('Version: ' + qsusb.version())
    qsusb.set_qs_values()

    qsusb.listen(print_item_callback, timeout=5)
    print("Started listening")
    try:
        # Do some test while listening
        if args.test_ids and len(args.test_ids) > 0:
            test_devices_set(qsusb.devices, args.test_ids.split(','))

        print("\n\nListening for 60 seconds (test buttons now)\n")
        sleep(60)
    except KeyboardInterrupt:
        pass
    finally:
        qsusb.stop()  # Close all threads
        print("Stopped listening")


if __name__ == "__main__":
    main()
