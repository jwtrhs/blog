#!/usr/bin/env python3
from setuptools import setup
import subprocess
import os

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

ver = (
    os.environ.get("PKGVER") or
    subprocess.run(
        ["git", "describe", "--tags"],
        stdout=subprocess.PIPE,
    ).stdout.decode().strip()
)

setup(
    name="blog",
    packages=[
        "server",
    ],
    version=ver,
    description="My personal blog",
    author="Jonathon Waterhouse",
    author_email="jon@wtrhs.com",
    url="https://git.sr.ht/~jwaterhouse/blog",
    install_requires=[
        "starlette",
        "uvicorn",
        "jinja2",
        "aiofiles",
        "markdown",
    ],
    license="BSD-3-Clause",
    include_package_data=True,
    python_requires=">=3.8",
)
