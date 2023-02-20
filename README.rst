**Cutthelog** is Python module and command-line tool to read unseen tailing part of log files.

The documentation of the module is available on readthedocs.
The tool description is below. The tool requires only Python 2 or Python 3 interpreter of almost any version (by default using Python 3) and its standard libraries. All code is located in a single file.

Here is an example of its work:

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


Installation
------------

From PyPI:

    ::
        sudo pip install cutthelog

or just download the tool file from Github:
https://raw.githubusercontent.com/yaznahar/cutthelog/main/cutthelog.py
make it executable and move to local bin folder

    ::
        chmod +x cutthelog.py; sudo mv cutthelog.py /usr/local/bin/cutthelog


How it works
------------

The tool stores offset and value of last line of each read file in a cache file. On next reading of that file it jumps to saved offset, read a line and compare its value with the saved one. If they / If don't it reads the file from the begining. At the end the tool update cache values of the file.

By default the cache file locates in user home folder with the name `.cutthelog`. If home folder is unavailable it tries to save cache in current working directory. You can redefine cache path by the option.

Usage
-----

You can get available option and its meaning by -h/--help option:

    ::
        $ cutthelog --help
