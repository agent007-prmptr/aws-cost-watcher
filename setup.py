from setuptools import setup, find_packages

setup(
    name='aws-cost-watcher',
    version='0.1.0',
    py_modules=['aws_cost_watcher'],
    install_requires=['boto3>=1.34.0'],
    entry_points={
        'console_scripts': [
            'aws-cost-watcher=aws_cost_watcher:main',
        ],
    },
    python_requires='>=3.8',
)
