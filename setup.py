#!/usr/bin/env python
# -*- coding: utf-8 -*-

from distutils.core import setup

import aeffect

with open('README.md') as stream:
  long_desc = stream.read()

setup(
    name = aeffect.__name__,
    version = aeffect.__version__,
    author = aeffect.__author__,
    author_email = aeffect.__email__,
    packages = ['aeffect'],
    license = aeffect.__license__,
    description = aeffect.__description__,
    long_description = long_desc,
    classifiers = [
        'Programming Language :: Python',
        'Operating System :: OS Independent',
        'Development Status :: 1 - Planning',
        'Environment :: No Input/Output (Daemon)',
        'Environment :: Console',
        'Intended Audience :: Information Technology',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Topic :: Database',
        'Topic :: Communications',
    ],
    entry_points={
        'console_scripts': [
            'aeffect = aeffect.__main__:main',
        ],
    }
)


