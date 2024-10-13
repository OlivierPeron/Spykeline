from setuptools import setup, find_packages
from setuptools.command.install import install
import subprocess
import os
from pathlib import Path

# Read the contents of your README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

class CustomInstallCommand(install):
    """Customized setuptools install command - clones a GitHub repository."""
    def run(self):
        install.run(self)
        # Clone the GitHub repository
        repo_url = 'https://github.com/GirardeauLab/probeinterface_library.git'
        clone_dir = os.path.expanduser("~/probeinterface_library")  # Use a directory in the user's home
        if not os.path.exists(clone_dir):
            subprocess.check_call(['git', 'clone', repo_url, clone_dir])
        else:
            print(f"{clone_dir} already exists. Skipping clone.")
        
        # Run the post-install script
        subprocess.check_call(['python', 'post_install.py'])

setup(
    name="spykeline",
    version="0.1.0",
    author="PERON Olivier",
    author_email="olivier.peron@inserm.fr",
    description="Spike sorting pipeline.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/GirardeauLab/Spykeline",
    packages=find_packages(),
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=[
        "docker==7.1.0",
        "matplotlib==3.9.1",
        "neo==0.13.0",
        "numba==0.60.0",
        "numpy==1.26.1",
        "pandas==2.2.2",
        "pillow==10.4.0",
        "probeinterface==0.2.21",
        "Rtree==1.3.0",
        "scikit-learn==1.5.1",
        "scipy==1.13.1",
        "spikeinterface==0.101.0rc0",
        "cuda-python==12.5.0"
    ],
    entry_points={
        'console_scripts': [
            'run_spykeline=spykeline.run_spykeline:main',
        ],
    },
    cmdclass={
        'install': CustomInstallCommand,
    },
)
