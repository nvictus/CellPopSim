import os
from setuptools import setup

PACKAGE = "cps"
NAME = "CellPopSim"
DESCRIPTION = "Framwork for agent-based simulation of cell populations"
README = os.path.join(os.path.dirname(__file__), 'README.md')
AUTHOR = "Nezar Abdennur"
AUTHOR_EMAIL = "nabdennur@gmail.com"
URL = ""
VERSION = __import__(PACKAGE).__version__

setup(
    name=NAME,
    version=VERSION,
    description=DESCRIPTION,
    long_description=README,
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    license="BSD",
    url=URL,
    packages=['cps'],
    classifiers=[
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
    ],
)


