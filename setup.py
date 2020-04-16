"""A setuptools based setup module."""

from setuptools import setup, find_packages
from codecs import open
from os import path


here = path.abspath(path.dirname(__file__))

# Get the long description from the README file.
with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

requirements = [
    "ifaddr>=0.1.0",
    "pyee>=7.0.0",
    "jsonschema>=3.2.0",
    "zeroconf>=0.21.0",
    "ujson",
    "httpx==0.12.*",
    "starlette==0.13.*",
    "uvicorn==0.11.*",
]

setup(
    name="aiowebthing",
    version="0.1.2",
    description="HTTP Web Thing async implementation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/hidaris/aiowebthing",
    author="hidaris",
    author_email="zuocool@gmail.com",
    keywords="async mozilla iot web thing webthing",
    packages=find_packages(exclude=["contrib", "docs", "tests"]),
    install_requires=requirements,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    license="MPL-2.0",
    project_urls={
        "Source": "https://github.com/hidaris/aiowebthing",
        "Tracker": "https://github.com/hidaris/aiowebthing/issues",
    },
    python_requires=">=3.6, <4",
)
