# setup_bytez.py
from setuptools import setup

setup(
    name='bytez-custom',
    version='0.1.0-custom',
    install_requires=[
        'numpy>=1.21.6,<1.27',  # Version plus flexible
        'charset-normalizer==3.1.0',
        'idna==3.4'
    ],
)