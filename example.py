#!/usr/bin/env python
"""Basic usage example and testing of pyqwikswitch."""

from time import sleep
import json
import pyqwikswitch


def print_devices(devs):
    """Print the reply from &devices() and highlight errors."""
    print("\n&devices\n[")
    for dev in devs:
        if not isinstance(dev[pyqwikswitch.PQS_VALUE], int):
            print("ERR decoding: not integer")
        elif dev[pyqwikswitch.PQS_VALUE] == -1:
            print("ERR decoding: -1?")
        qcord = pyqwikswitch.decode_qwikcord(dev[pyqwikswitch.QS_VALUE])
        if qcord is not None:
            print('  qwikcord (CTAVG, CTsum) = ' + str(qcord))
        print(dev[pyqwikswitch.QS_VALUE] + ' --> ' +
              str(dev[pyqwikswitch.PQS_VALUE]))
        print('  ' + str(dev))
    print(']\n')


def print_item_callback(item):
    """Print an item callback, used by &listen."""
    print('&listen [{}, {}={}]'.format(
        item.get('cmd', ''),
        item.get('id', ''),
        item.get('data', '')))


def test_qsusb_set(qsusb, ids):
    """Test the set method for ids passed in.

    In thie example using --test_ids @id1,@id2.
    """
    for qsid in ids:
        for value in (100, 50, 0):
            sleep(3)
            print("\nSet {} = {}".format(qsid, value))
            val = qsusb.set(qsid, value)
            print("   --> result: {}".format(val))
            print(qsusb.devices(qsid))
        sleep(2)


def main():
    """QSUsb class quick test."""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', help='QSUSB URL [http://127.0.0.1:2020]',
                        default='http://127.0.0.1:2020')
    parser.add_argument('--file', help='a test file from /&devices')
    parser.add_argument('--test_ids', help='List of test IDs',
                        default='@000001,@0c2700,@0ac2f0')
    args = parser.parse_args()

    if args.file:
        with open(args.file) as data_file:
            data = json.load(data_file)
        qsusb = pyqwikswitch.QSUsb('', _offline=True)
        print_devices(qsusb.devices(devices=data))
        return

    print('Execute a basic test on server: {}\n'.format(args.url))

    qsusb = pyqwikswitch.QSUsb(args.url)
    print('Version: ' + qsusb.version())
    print_devices(qsusb.devices())

    qsusb.listen(print_item_callback, timeout=5)
    print("Started listening")
    try:
        # Do some test while listening
        if args.test_ids and len(args.test_ids) > 0:
            test_qsusb_set(qsusb, args.test_ids.split(','))

        print("\n\nListening for 20 seconds (test buttons now)\n")
        sleep(20)
    except KeyboardInterrupt:
        pass
    finally:
        qsusb.stop()  # Close all threads
        print("Stopped listening")

if __name__ == "__main__":
    main()
