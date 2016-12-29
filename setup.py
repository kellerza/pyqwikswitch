#!/usr/bin/env python
"""pyqwikswitch library setup."""

from setuptools import setup

setup(name='pyqwikswitch',
      version='0.4',
      description='Library to interface Qwikswitch USB Hub',
      url='https://github.com/kellerza/pyqwikswitch',
      download_url = 'https://github.com/kellerza/pyqwikswitch/tarball/0.4',
      author='Johann Kellerman',
      author_email='kellerza@gmail.com',
      license='MIT',
      packages=['pyqwikswitch'],
      install_requires=['requests>=2,<3'],
      zip_safe=True)
