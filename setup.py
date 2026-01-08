"""
Setup configuration for Claude Code Python MVP

Python 3.8.10 Strict Compatibility
Windows 7 + Internal Network (DeepSeek R1 70B)
"""

from pathlib import Path
from typing import List

# Read requirements.txt for dependencies
def read_requirements() -> List[str]:
    """Read requirements.txt, filtering comments and empty lines."""
    requirements_file = Path(__file__).parent / "requirements.txt"
    with open(requirements_file, encoding="utf-8") as f:
        return [
            line.strip()
            for line in f
            if line.strip()
            and not line.startswith("#")
            and not line.startswith("--")
        ]


# Read README for long description
def read_readme() -> str:
    """Read README.md for long description."""
    readme_file = Path(__file__).parent / "README.md"
    if readme_file.exists():
        with open(readme_file, encoding="utf-8") as f:
            return f.read()
    return "Claude Code Python MVP - AI-native development workflow engine"


from setuptools import find_packages, setup

setup(
    name="claude-code-mvp",
    version="0.1.0",
    description="Claude Code Python MVP - AI-native development workflow engine",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="Claude Code Development Team",
    python_requires=">=3.8.10,<3.10",
    packages=find_packages(exclude=["tests", "tests.*"]),
    install_requires=read_requirements(),
    extras_require={
        "dev": [
            "pytest==7.2.2",
            "pytest-cov==4.1.0",
            "pytest-mock==3.12.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "claude-code=claude_code.cli.main:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Operating System :: OS Independent",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: Microsoft :: Windows :: 7",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
    ],
)
