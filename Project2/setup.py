# setup.py
from setuptools import setup, find_packages

setup(
    name="live_feed",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        'xlwings>=0.27.0',
        'pandas>=1.3.0',
        'numpy>=1.21.0',
        'requests>=2.26.0',
        'smartapi-python>=1.2.0',
        'pyotp>=2.6.0',
        'openpyxl>=3.0.9',
    ],
)