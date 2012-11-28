#!/usr/bin/env python
# -*- coding: utf-8 -*-

from distutils.core import setup

import carboneffect

with open('README.md') as stream:
  long_desc = stream.read()

setup(
    name = carboneffect.__name__,
    version = carboneffect.__version__,
    author = carboneffect.__author__,
    author_email = carboneffect.__email__,
    packages = ['carboneffect'],
    url = 'https://github.com/IndieInfoTech/Docket',
    license = carboneffect.__license__,
    description = carboneffect.__description__,
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
)


