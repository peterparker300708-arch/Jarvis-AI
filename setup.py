"""Setup configuration for the Jarvis AI package."""

from setuptools import find_packages, setup

with open("README.md", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", encoding="utf-8") as fh:
    # Strip blank lines and comments
    requirements = [
        line.strip()
        for line in fh
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="jarvis-ai",
    version="1.0.0",
    author="Jarvis AI Team",
    author_email="jarvis@example.com",
    description="Jarvis AI – Complete System Control Assistant",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/Jarvis-AI",
    packages=find_packages(exclude=["tests*", "*.pyc"]),
    python_requires=">=3.9",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "jarvis=jarvis:main",
        ],
    },
    include_package_data=True,
    package_data={
        "web": [
            "templates/*.html",
            "static/css/*.css",
            "static/js/*.js",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: System :: Systems Administration",
    ],
    keywords="jarvis ai assistant voice system-control",
)
