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
    version="0.1.2",
    license='MIT',
    install_requires=[
        'pyyaml',
    ],
    keywords='plaid plaidcloud',
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Unix",
    ],
    packages=['plaidcloud.config'],
    long_description=long_description,
    long_description_content_type='text/markdown',
    python_requires='>=3.7',
)
