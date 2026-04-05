"""
Setup script for Jarvis AI - Advanced Edition.
"""

from setuptools import setup, find_packages


with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = [
        line.strip()
        for line in f
        if line.strip() and not line.startswith("#") and not line.startswith("//")
    ]

setup(
    name="jarvis-ai",
    version="2.0.0",
    author="Jarvis AI Team",
    description="Advanced AI Assistant with Complete System Control",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/peterparker300708-arch/Jarvis-AI",
    packages=find_packages(exclude=["tests*", "*.tests.*"]),
    python_requires=">=3.9",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "jarvis=jarvis:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    keywords="jarvis ai assistant voice system-control automation",
    project_urls={
        "Bug Reports": "https://github.com/peterparker300708-arch/Jarvis-AI/issues",
        "Source": "https://github.com/peterparker300708-arch/Jarvis-AI",
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.yml", "*.json"],
        "web": ["templates/**/*.html", "static/**/*"],
    },
)
