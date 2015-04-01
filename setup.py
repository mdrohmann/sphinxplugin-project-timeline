# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


requires = [
    'sphinxcontrib-blockdiag', 'blockdiag>=1.5.0', 'Sphinx>=0.6', 'setuptools',
    'python-dateutil', 'roman', 'docutils']

setup(
    name='sphinxcontrib-blockdiag',
    version='0.1.0',
    #    url='',
    #    download_url='',
    license='BSD',
    author='Martin Drohmann',
    author_email='mdrohmann@gmail.com',
    description='Sphinx Project timeline extension',
    long_description=open("README.rst").read(),
    zip_safe=False,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Topic :: Documentation',
        'Topic :: Utilities',
    ],
    platforms='any',
    packages=find_packages(),
    include_package_data=True,
    install_requires=requires,
)
