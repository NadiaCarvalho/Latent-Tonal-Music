"""This module sets up the Python package"""

from setuptools import setup, find_packages

with open("README.md", "r",  encoding="ascii") as readme_file:
    readme = readme_file.read()
    readme_file.close()

with open("requirements.txt", "r",  encoding="ascii") as requirements_file:
    requirements = requirements_file.read()
    requirements_file.close()

setup(
    name="harmrep",
    version="0.0.1",
    author="XXX",
    author_email="XXX",
    description="Exploring Latent Spaces of Tonal Music using Variational Autoencoders",
    long_description=readme,
    long_description_content_type="text/markdown",
    url="https://github.com/XXX-AIMC2023/Latent-Tonal-Music.git",
    packages=find_packages(),
    install_requirements=requirements,
    classifiers=[
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)"
    ]
)
