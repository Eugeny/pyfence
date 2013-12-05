#!/usr/bin/env python

from distutils.core import setup
from setuptools import find_packages

from pyfence import __version__

setup(
    name='pyfence',
    version=__version__,
    install_requires=[
    ],
    description='Automatic type verificator for Python',
    author='Eugene Pankov',
    author_email='e@ajenti.org',
    url='http://ajenti.org/',
    packages=find_packages(exclude=['*test*']),
)
