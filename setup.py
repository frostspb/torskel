from distutils.core import setup
from setuptools import find_packages

VERSION = '0.1.42'

setup(
    name='torskel',
    version=VERSION,
    packages=find_packages(),
    url='https://github.com/frostspb/torskel',
    license='MIT',
    author='Frostspb',
    description='Python package with skeleton of the base Tornado application',
	long_description="""Contains basic functions for logging, asynchronous redis,
	support for reactJS and asynchronous http request Only Python 3.5+""",
    keywords=["tornado"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
    ],
    install_requires=[
        'tornado>=4.5.2',
    ],
)
