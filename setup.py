#!/usr/bin/env python

import os
from setuptools import setup, find_packages

import towel

setup(name='towel',
      version=towel.__version__,
      description='Keeping you DRY since 2010',
      long_description=open(os.path.join(os.path.dirname(__file__), 'README')).read().decode('utf-8'),
      author='Matthias Kestenholz',
      author_email='mk@feinheit.ch',
      url='http://github.com/matthiask/towel/',
      license='BSD License',
      platforms=['OS Independent'],
      packages=find_packages(),
      include_package_data=True,
      )
