#!/usr/bin/env python3
"""
GiljoAI MCP - Package Setup Configuration
Setuptools configuration for pip installation
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
req_file = Path(__file__).parent / "requirements.txt"
requirements = []
if req_file.exists():
    requirements = [
        line.strip()
        for line in req_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="giljo-mcp",
    version="2.0.0",
    description="GiljoAI MCP Coding Orchestrator - Multi-agent orchestration system",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="GiljoAI Team",
    author_email="support@giljoai.com",
    url="https://github.com/yourusername/giljo-mcp",
    license="MIT",

    # Package discovery
    packages=find_packages(where="src"),
    package_dir={"": "src"},

    # Dependencies
    install_requires=requirements,

    # Python version requirement
    python_requires=">=3.10",

    # Entry points
    entry_points={
        "console_scripts": [
            "giljo-mcp=giljo_mcp.__main__:main",
        ],
    },

    # Classifiers
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],

    # Include package data
    include_package_data=True,
    zip_safe=False,
)
