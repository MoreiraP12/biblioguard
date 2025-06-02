"""
Setup script for the Paper Reference Auditor.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="paper-auditor",
    version="1.0.0",
    author="Paper Auditor Team",
    author_email="contact@paper-auditor.com",
    description="A tool for auditing research paper references",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/paper-auditor/paper-auditor",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering",
        "Topic :: Text Processing :: Linguistic",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "paper-auditor=paper_auditor.cli:cli",
        ],
    },
    include_package_data=True,
    zip_safe=False,
) 