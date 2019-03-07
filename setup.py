from distutils.core import setup
from setuptools import find_packages
import torskel
VERSION = torskel.version

setup(
    name='torskel',
    version=VERSION,
    packages=find_packages(),
    url='https://github.com/frostspb/torskel',
    license='MIT',
    author='Frostspb',
    description='Python package with skeleton of the base Tornado application',
    long_description="""Contains basic functions for logging,
    asynchronous redis and asynchronous http request out of box
    Only Python 3.7+""",
    keywords=["tornado"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3.7",
    ],
    install_requires=[
        'xmltodict>=0.11.0',
        'user-agents>=1.1.0',
        'tornado>=5.1',
        'pyjwt>=1.7.1',
        'python-jwt>=3.2.4',
    ],
)
