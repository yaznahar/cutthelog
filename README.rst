**Cutthelog** is Python module and command-line tool to print unseen tailing part of a log file.

The documentation of the module is available in the code (import to readthedocs in progress). The tool documentation is below.

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

or just download the tool file from `github <https://raw.githubusercontent.com/yaznahar/cutthelog/main/cutthelog.py>`_, make it executable and move to proper bin folder e.g.

::

    $ chmod +x cutthelog.py; sudo mv cutthelog.py /usr/local/bin/cutthelog

Usage
-----

In most cases it's enough to pass a logfile path:

::

    $ cutthelog /var/log/syslog

One of an application of the tool is checking a rate of some kind of log messages:

1. First, you should cache current log position by command

::

   $ sudo -u syslog cutthelog /var/log/syslog > /dev/null

2. Then you should create cron job like

::

    MAILTO="admin@example.org"

    */10 * * * * syslog [ $(cutthelog /var/log/syslog | grep 'error' | wc -l) -gt 3 ] && echo "Too many errors"

3. To process rotated logs more accurately you should add similar command as a prerotate script.


To see all available options you should use the ``-h/--help`` option:

::

    $ cutthelog --help
