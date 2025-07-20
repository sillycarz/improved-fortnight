"""
Setup script for reflectpause-core package.

This is maintained for backward compatibility.
The primary build configuration is in pyproject.toml.
"""

from setuptools import setup, find_packages

setup(
    name="reflectpause-core",
    version="0.1.0",
    packages=find_packages(include=["reflectpause_core*"]),
    python_requires=">=3.8",
)