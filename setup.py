#!/usr/bin/env python
import pyfence
pyfence.options['off'] = True

from distutils.core import setup
from setuptools import find_packages


setup(
    name='pyfence',
    version=pyfence.__version__,
    install_requires=[
    ],
    description='Automatic type verificator for Python',
    author='Eugene Pankov',
    author_email='e@ajenti.org',
    url='http://eugeny.github.io/pyfence/',
    packages=find_packages(),
    scripts=['fence'],
)
