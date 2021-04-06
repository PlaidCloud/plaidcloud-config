from setuptools import setup

from os import path
this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='plaidcloud-config',
    version="0.1.0",
    author='Garrett Bates',
    author_email='garrett.bates@tartansolutions.com',
    install_requires=[
        'pyyaml',
    ],
    packages=['plaidcloud.config'],
    # tests_require=test_deps,
    long_description=long_description,
    long_description_content_type='text/markdown',
)
