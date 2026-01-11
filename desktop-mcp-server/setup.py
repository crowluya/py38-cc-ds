"""
Desktop MCP Server - Setup

Python 3.8.10 compatible
"""

from setuptools import setup, find_packages

setup(
    name="desktop-mcp-server",
    version="0.1.0",
    description="MCP server for desktop automation with EasyOCR",
    author="DeepCode",
    python_requires=">=3.8",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    install_requires=[
        # Core dependencies - install separately based on platform
        # Windows 7: pip install pyautogui==0.9.53 easyocr opencv-python-headless numpy Pillow==9.5.0
        # macOS: pip install pyautogui easyocr opencv-python-headless numpy Pillow
    ],
    extras_require={
        "dev": [
            "pytest==7.2.2",
            "pytest-cov==4.0.0",
        ],
        "windows": [
            "pyautogui==0.9.53",
            "easyocr",
            "opencv-python-headless",
            "numpy",
            "Pillow==9.5.0",
        ],
        "macos": [
            "pyautogui",
            "easyocr",
            "opencv-python-headless",
            "numpy",
            "Pillow",
        ],
    },
    entry_points={
        "console_scripts": [
            "desktop-mcp=desktop_mcp.__main__:main",
        ],
    },
)
