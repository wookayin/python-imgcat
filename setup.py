#!/usr/bin/env python

import os
import re

from setuptools import setup


__PATH__ = os.path.abspath(os.path.dirname(__file__))


def read_readme():
    with open('README.md') as f:
        return f.read()

def read_version():
    # importing the package causes an ImportError :-)
    with open(os.path.join(__PATH__, 'imgcat/__init__.py')) as f:
        version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                                  f.read(), re.M)
    if version_match:
        return str(version_match.group(1))
    raise RuntimeError("Unable to find __version__ string")


install_requires = [
]

tests_requires = [
    'pytest',
    'numpy',
    'torch',
    'tensorflow>=2.0',
    'matplotlib>=3.3',
    'Pillow',
]

__version__ = read_version()


setup(
    name='imgcat',
    version=__version__,
    license='MIT',
    description='imgcat as Python API and CLI',
    long_description=read_readme(),
    long_description_content_type='text/markdown',
    url='https://github.com/wookayin/python-imgcat',
    author='Jongwook Choi',
    author_email='wookayin@gmail.com',
    keywords='imgcat iterm2 matplotlib',
    classifiers=[
        # https://pypi.python.org/pypi?%3Aaction=list_classifiers
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    packages=['imgcat'],
    python_requires='>=3.6',
    install_requires=install_requires,
    extras_require={'test': tests_requires},
    setup_requires=['pytest-runner<5.0'],
    tests_require=tests_requires,
    entry_points={
        'console_scripts': ['imgcat=imgcat:main'],
    },
    include_package_data=True,
    zip_safe=False,
    cmdclass={
    },
)
