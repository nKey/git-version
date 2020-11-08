#!/usr/bin/env python
import codecs
import os

from setuptools import setup
from setuptools import find_packages


def read(*parts):
    path = os.path.join(os.path.dirname(__file__), *parts)
    with codecs.open(path, encoding='utf-8') as fobj:
        return fobj.read()


setup(
    name='git-version',
    version="1.2.0.0",
    description='Git version manager',
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    url='https://www.nkey.com.br/',
    project_urls={
        'Documentation': 'https://github.com/nKey/git-version',
        'Changelog': 'https://github.com/nKey/git-version/blob/release/CHANGELOG.md',
        'Source': 'https://github.com/nKey/git-version',
        'Tracker': 'https://github.com/nKey/git-version/issues',
    },
    author='nKey, Inc.',
    license='Apache License 2.0',
    py_modules=["version"],
    include_package_data=True,
    python_requires='>=2.7',
    entry_points={
        'console_scripts': ['git-version=version:main'],
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
)