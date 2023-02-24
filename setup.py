from setuptools import setup
from cutthelog import __version__, __doc__


with open('README.rst') as fhandler:
    long_description = fhandler.read()

setup(
    name='cutthelog',
    version=__version__,
    py_modules=['cutthelog'],
    author='Alexander Larin',
    author_email='yaznahar@yandex.ru',
    url='https://github.com/yaznahar/cutthelog',
    description=__doc__.splitlines()[0],
    long_description=long_description,
    license='MIT license',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Topic :: System :: Systems Administration',
        'Topic :: Text Processing :: Filters',
        'Topic :: Utilities',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: Implementation :: CPython',
    ],
    entry_points={
        'console_scripts': [
           'cutthelog=cutthelog:main'
        ],
    },
)
