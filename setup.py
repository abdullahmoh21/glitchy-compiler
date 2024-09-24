from setuptools import setup, find_packages

setup(
    name="GlitchyCompiler",
    version="1.0",
    packages=find_packages(),  
    install_requires=[
        "llvmlite",  
    ],
    entry_points={
        'console_scripts': [
            'glitchy=Compiler.compile:main',  # so you can call from any directory
        ]
    },
    include_package_data=True,
    test_suite='unittest',
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)