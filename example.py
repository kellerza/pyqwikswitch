"""Basic usage example and testing of pyqwikswitch."""

import argparse
import asyncio
import json
from collections.abc import Callable
from pathlib import Path
from time import sleep

from aiohttp import ClientSession

from pyqwikswitch.async_ import QSUsb
from pyqwikswitch.qwikswitch import QS_ID, QS_VALUE, QSDevices, QSType, decode_qwikcord


def print_bad_data(json):
    """Print error if ID invalid."""
    for dev in json:
        if QS_ID not in dev:
            print("**ERR NO ID:", dev)


DEVS: QSDevices = None  # type: ignore[assignment]


def print_devices_change_callback(
    key: str, new: float, cb: Callable[[], None] | None = None
):
    """Print the reply from &devices() and highlight errors."""
    dev = DEVS[key]
    print("- ", new, " ", dev)
    if dev.qstype == QSType.unknown:
        print(" ERR decoding")
    elif dev.value == -1:
        print(" ERR decoding: -1?")
    qcord = decode_qwikcord(dev.data[QS_VALUE])  # type: ignore[arg-type]
    if qcord is not None:
        print(" qwikcord (CTAVG, CTsum) = " + str(qcord))


def print_item_callback(item):
    """Print an item callback, used by &listen."""
    print(
        "&listen [{}, {}={}]".format(
            item.get("cmd", ""), item.get("id", ""), item.get("data", "")
        )
    )


def test_devices_set(devices, ids):
    """Test the set method for ids passed in.

    In this example using --test_ids @id1,@id2.
    """
    for _id in ids:
        for value in (10, 9):
            sleep(3)
            print(f"\nSet {_id} = {value}")
            val = devices.set_value(_id, value)
            print(f"   --> result: {val}")
            print(devices[_id])
        sleep(2)


async def main():
    """Quick test for QSUsb class."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url",
        help="QSUSB URL [http://127.0.0.1:2020]",
        default="http://127.0.0.1:2020",
    )
    parser.add_argument("--file", help="a test file from /&devices")
    parser.add_argument(
        "--test_ids", help="List of test IDs", default="@0c2700,@0ac2f0"
    )
    args = parser.parse_args()

    if args.file:
        with Path(args.file).open(encoding="utf-8") as data_file:  # noqa: ASYNC230
            data = json.load(data_file)
        global DEVS  # noqa: PLW0603
        DEVS = QSDevices(print_devices_change_callback, print_devices_change_callback)
        print_bad_data(data)
        # await DEVS.set_value(data)
        return

    print(f"Execute a basic test on server: {args.url}\n")

    def qs_to_value(key: str, new: float):
        print(f" --> New value: {key}={new}")

    session = ClientSession()

    qsusb = QSUsb(args.url, 1, qs_to_value, session)
    print("Version: " + await qsusb.version())
    # await qsusb.set_qs_value()

    print("Started listening")
    qsusb.listen(print_item_callback)
    try:
        # Do some test while listening
        if args.test_ids and len(args.test_ids) > 0:
            test_devices_set(qsusb.devices, args.test_ids.split(","))

        print("\n\nListening for 60 seconds (test buttons now)\n")
        await asyncio.sleep(60)
    except KeyboardInterrupt:
        pass
    finally:
        qsusb.stop()  # Close all threads
        print("Stopped listening")


if __name__ == "__main__":
    asyncio.run(main())
