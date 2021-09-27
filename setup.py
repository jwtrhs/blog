#!/usr/bin/env python3
from setuptools import setup
import subprocess
import os

if os.path.exists("README.md"):
    with open("README.md", "r", encoding="utf-8") as f:
        long_description = f.read()
else:
    long_description = "My personal blog"


with open("requirements.txt") as f:
    requirements = f.read().splitlines()


version = (
    os.environ.get("PKGVER")
    or subprocess.run(
        ["git", "describe", "--tags"],
        stdout=subprocess.PIPE,
    )
    .stdout.decode()
    .strip()
)


setup(
    name="blog",
    packages=[
        "server",
    ],
    version=version,
    description="My personal blog",
    long_description=long_description,
    author="Jonathon Waterhouse",
    author_email="jon@wtrhs.com",
    url="https://git.sr.ht/~jwaterhouse/blog",
    install_requires=requirements,
    license="BSD-3-Clause",
    include_package_data=True,
    python_requires=">=3.8",
)
