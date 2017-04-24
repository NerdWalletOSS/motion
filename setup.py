from setuptools import setup, find_packages

with open('VERSION') as version_fd:
    version = version_fd.read().strip()

install_requires = [
    'kinesis-python>=0.0.5,<1.0',
    'click>=6.6,<7.0',
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
    entry_points={
        'console_scripts': [
            'motion = motion.cli:main'
        ]
    }
)
