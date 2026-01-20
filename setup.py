"""This module sets up the Python package for harmrep"""

from setuptools import setup, find_packages
from pathlib import Path

# Use pathlib for cleaner path handling
this_directory = Path(__file__).parent

# Read the README using UTF-8 to avoid encoding errors on different OSs
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

# Read requirements and convert to a list
def parse_requirements(filename):
    with open(this_directory / filename, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="harmrep",
    version="0.1.0",  # Incrementing to 0.1.0 is standard for first functional release
    author="Nádia Carvalho",
    author_email="nadiacarvalho118@gmail.com",
    description="Exploring Latent Spaces of Tonal Music using Variational Autoencoders",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/nadiacarvalho118-AIMC2023/Latent-Tonal-Music",
    packages=find_packages(),
    
    # Corrected argument name: install_requires (not install_requirements)
    install_requires=parse_requirements("requirements.txt"),
    
    python_requires=">=3.10", # Explicitly state version support
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Topic :: Multimedia :: Sound/Audio :: Analysis",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    project_urls={
        "Bug Tracker": "https://github.com/XXX-AIMC2023/Latent-Tonal-Music/issues",
        "Source Code": "https://github.com/XXX-AIMC2023/Latent-Tonal-Music",
    },
)
