from setuptools import setup, find_packages

with open('VERSION') as version_fd:
    version = version_fd.read().strip()

with open('README.md') as readme_fd:
    long_description = readme_fd.read()

install_requires = [
    'click>=6.6,<7.0',
    'kinesis-python>=0.2.1,<0.9',
    'offspring>=0.1.1,<1.0',
    'six>=1.12.0,<2.0'
]

setup(
    name='motion',
    version=version,
    install_requires=install_requires,
    packages=find_packages('src'),
    package_dir={'': 'src'},
    author='Evan Borgstrom',
    author_email='eborgstrom@nerdwallet.com',
    license='Apache 2',
    description='High-level library for dispatching and responding to tasks via AWS Kinesis',
    long_description=long_description,
    long_description_content_type="text/markdown",
    entry_points={
        'console_scripts': [
            'motion = motion.cli:main'
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Programming Language :: Python",
        "Topic :: Internet",
        "Topic :: Software Development :: Libraries",
    ],
)
