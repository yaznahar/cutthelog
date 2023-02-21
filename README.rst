**Cutthelog** is Python module and command-line tool to print unseen tailing part of a log file.

| The documentation of the module is available on readthedocs.
The tool documentation is below.

On each execution the tool saves offset and value of last line of a file in cache. On next reading of the same file it jumps to that offset and checks the last line value. If the check passed the tool prints file content from current position. If the check failed the tool prints the file from the begining.

Here is an demo:

.. code-block::

    $ echo -e "one\ntwo\nthree" > example
    $ cutthelog example
    one
    two
    three
    $ cutthelog example
    $ echo -e "four\nfive\nsix" >> example
    $ cutthelog example
    four
    five
    six
    $ cutthelog example
    $ echo -e "seven\neight\nnine\nten\neleven\ntwelve" > example
    $ cutthelog example
    seven
    eight
    nine
    ten
    eleven
    twelve

The tool requires only Python 2 or Python 3 interpreter of almost any version (by default using Python 3) and its standard libraries. All the code is located in a single file.

By default the cache is stored in user home folder with the name ``.cutthelog``. If the home folder is unavailable the tool creates cache in current working directory. You can specify cache path by the option.


Installation
------------

From PyPI:

::

    $ sudo pip install cutthelog

| or just download the tool file from Github:
| https://raw.githubusercontent.com/yaznahar/cutthelog/main/cutthelog.py
make it executable and move to proper bin folder e.g.

::

    $ chmod +x cutthelog.py; sudo mv cutthelog.py /usr/local/bin/cutthelog

Usage
-----

You can get available option and its meaning by -h/--help option:

::

    $ cutthelog --help
