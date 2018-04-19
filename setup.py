#!/usr/bin/env python3
# python setup.py sdist
# twine upload dist/*
"""pyqwikswitch library setup."""
from setuptools import setup

REQUIREMENTS = ['attrs', 'requests']
VERSION = '0.8'

setup(name='pyqwikswitch',
      version=VERSION,
      description='Library to interface Qwikswitch USB Hub',
      url='https://github.com/kellerza/pyqwikswitch',
      download_url='https://github.com/kellerza/pyqwikswitch/tarball/{}'
      .format(VERSION),
      author='Johann Kellerman',
      author_email='kellerza@gmail.com',
      license='MIT',
      packages=['pyqwikswitch'],
      install_requires=REQUIREMENTS,
      zip_safe=True)
