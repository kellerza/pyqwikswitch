#!/usr/bin/env python3
"""pyqwikswitch library setup."""
from pathlib import Path
from setuptools import setup

REQUIREMENTS = ["attrs", "requests"]
VERSION = "0.94"

setup(
    name="pyqwikswitch",
    version=VERSION,
    description="Library to interface Qwikswitch USB Hub",
    long_description=Path("README.md").read_text(),
    long_description_content_type="text/markdown",
    url="https://github.com/kellerza/pyqwikswitch",
    download_url="https://github.com/kellerza/pyqwikswitch/tarball/{}".format(VERSION),
    author="Johann Kellerman",
    author_email="kellerza@gmail.com",
    license="MIT",
    packages=["pyqwikswitch"],
    install_requires=REQUIREMENTS,
    zip_safe=True,
)
