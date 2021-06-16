#!/usr/bin/env python
# coding=utf-8

__author__ = "Garrett Bates"
__copyright__ = "© Copyright 2020-2021, Tartan Solutions, Inc"
__credits__ = ["Garrett Bates"]
__license__ = "Apache 2.0"
__version__ = "0.1.9"
__maintainer__ = "Garrett Bates"
__email__ = "garrett.bates@tartansolutions.com"
__status__ = "Development"

from setuptools import setup

from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='plaidcloud-config',
    author='Garrett Bates',
    author_email='garrett.bates@tartansolutions.com',
    description="Basic utility to parse a configuration for PlaidCloud application stack.",
    version="0.1.9",
    license='Apache 2.0',
    install_requires=[
        'pyyaml',
    ],
    keywords='plaid plaidcloud',
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: Unix",
    ],
    packages=['plaidcloud.config'],
    long_description=long_description,
    long_description_content_type='text/markdown',
    python_requires='>=3.7',
)
