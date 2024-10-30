import subprocess
import sys
from setuptools import setup, find_packages
from setuptools.command.install import install

class checkClang(install):
    def run(self):
        try:
            subprocess.run(['clang', '--version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print("Clang is installed.")
        except subprocess.CalledProcessError:
            print("Error: Clang is not installed. Please install Clang and ensure it's in your PATH.")
            sys.exit(1) 

        install.run(self)

setup(
    name="GlitchyCompiler",
    version="1.0",
    packages=find_packages(),
    install_requires=[
        "llvmlite",  
        "rich",      
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
        'install': checkClang,  # Ensure clang is installed for linking
    },
)
