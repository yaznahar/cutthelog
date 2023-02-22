**Cutthelog** is a Python module and command-line tool to print an unseen tailing part of a log file.

The documentation of the module is available in the code (import to readthedocs in progress). You can find the tool documentation below.

On each execution, the tool saves an offset and value of the last line of a file in a cache. On the next reading of the same file, it jumps to that offset and checks the last line value. If the check passed the tool prints file content from the current position. If the check failed the tool prints the file from the beginning.

Here is a demo:

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

The tool requires only Python 2 or Python 3 interpreter of almost any version (by default using Python 3) and its standard libraries. All the code is located in the single file.

By default, the cache is stored in the user's home folder with the name ``.cutthelog``. If the home folder is unavailable the tool creates the cache in the working directory. You can specify the cache path by the ``-c/--cache-file`` option.


Installation
------------

From PyPI:

::

    $ sudo pip install cutthelog

or just download the tool file from `github <https://raw.githubusercontent.com/yaznahar/cutthelog/main/cutthelog.py>`_, make it executable and move it to the proper bin folder e.g.

::

    $ chmod +x cutthelog.py; sudo mv cutthelog.py /usr/local/bin/cutthelog

Usage
-----

In most cases it's enough to pass a logfile path:

::

    $ cutthelog /var/log/syslog

You can apply the tool to check the rate of some kinds of log messages:

1. First, you should save the current log position to the cache by command

::

   $ sudo -u syslog cutthelog /var/log/syslog > /dev/null

2. Then you should create a cron job something like

::

    MAILTO="admin@example.org"

    */10 * * * * syslog [ $(cutthelog /var/log/syslog | grep 'error' | wc -l) -gt 3 ] && echo "Too many errors"

3. To process rotated logs more accurately you should add similar command as a pre-rotate script.


To see all available options you should use the ``-h/--help`` option:

::

    $ cutthelog --help
