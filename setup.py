from setuptools import setup

setup(
    name='readcode',
    version='1.0',
    py_modules=['run', 'lexer', 'parser', 'executor', 'web_generator', 'server_generator', 'ml_engine'],
    entry_points={
        'console_scripts': [
            'readcode=run:main',
        ],
    },
)
