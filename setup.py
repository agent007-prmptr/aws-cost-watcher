from setuptools import setup, find_packages

setup(
    name="aws-cost-watcher",
    version="0.2.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "boto3>=1.34.0",
        "click>=8.0.0",
        "pyyaml>=6.0",
    ],
    entry_points={
        "console_scripts": [
            "aws-cost-watcher=aws_cost_watcher.cli:main",
        ],
    },
    python_requires=">=3.8",
    author="",
    description="Get notified before your AWS bill surprises you",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)