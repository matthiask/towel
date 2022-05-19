#!/usr/bin/env python3

import os

from setuptools import find_packages, setup


def read(filename):
    return open(os.path.join(os.path.dirname(__file__), filename)).read()


setup(
    name="towel",
    version=__import__("towel").__version__,
    description="Keeping you DRY since 2010",
    long_description=read("README.rst"),
    author="Matthias Kestenholz",
    author_email="mk@feinheit.ch",
    url="http://github.com/matthiask/towel/",
    license="BSD License",
    platforms=["OS Independent"],
    packages=find_packages(),
    package_data={
        "": ["*.html", "*.txt"],
        "towel": [
            "locale/*/*/*.*",
            "static/towel/*.*",
            "static/towel/*/*.*",
            "templates/*.*",
            "templates/*/*.*",
            "templates/*/*/*.*",
            "templates/*/*/*/*.*",
        ],
    },
    install_requires=["Django>=3.2"],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Software Development",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
    zip_safe=False,
)
