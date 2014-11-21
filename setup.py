#!/usr/bin/env python3

from distutils.core import setup


setup(
    name="eventdigest",
    version="0",
    description="sends emails containing digests of banking and RSS events",
    author="Michael Enßlin",
    author_email="michael@ensslin.cc",
    packages=("eventdigest", "localshortener",),
)
