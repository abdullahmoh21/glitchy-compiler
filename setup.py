import subprocess
import sys
from setuptools import setup, find_packages
from setuptools.command.install import install

class CustomInstallCommand(install):
    def run(self):
        try:
            # Check if llvm-as is installed
            subprocess.run(['llvm-as', '--version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print("LLVM is installed.")
        except subprocess.CalledProcessError:
            print("Error: LLVM is not installed. Please install LLVM from https://llvm.org/")
            sys.exit(1)  # Exit with error if LLVM is not installed

        install.run(self)

setup(
    name="GlitchyCompiler",
    version="1.0",
    packages=find_packages(),
    install_requires=[
        "llvmlite",
    ],
    entry_points={
        'console_scripts': [
            'glitchy=Compiler.compile:main',
        ]
    },
    include_package_data=True,
    test_suite='unittest',
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: MIT License",
    ],
    python_requires='>=3.6',
    cmdclass={
        'install': CustomInstallCommand,  # Use the custom install class
    },
)
