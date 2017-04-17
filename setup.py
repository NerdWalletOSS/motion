from setuptools import setup, find_packages

with open('VERSION') as version_fd:
    version = version_fd.read().strip()

install_requires = [
    'kinesis-python>=0.0.1,<1.0'
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
    description='High-level library for dispatching and responding to tasks via AWS Kinesis'
)
