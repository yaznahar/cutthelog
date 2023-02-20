#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Print only unseen tailing part of log file"""


import argparse
import logging
import os
import shutil
import sys
import tempfile

VERSION = (1, 0, 0)
__version__ = '.'.join(map(str, VERSION))
DEFAULT_POSITION = (0, b'')
LOG_FORMAT = '%(levelname)s: %(message)s'
CACHE_DELIMITER = '##'
EOL = b'\n'
CACHE_FILENAME = '.cutthelog'
HELPS = {
    'logfile': 'path of the file to read',
    'cache_file': ('path to the cache file (by default used {} in the home or '
                   'current folder)'.format(CACHE_FILENAME)),
    'cache_delimiter': 'delimiter used inside cache record (by default "{}")'.format(CACHE_DELIMITER),
    'verbose': 'enable verbose mode',
    'version': 'print utility version and exit',
}


class CutthelogError(Exception):
    """General module exception"""


class CutthelogCacheError(CutthelogError):
    """Error on cache interaction"""


class CutTheLog:
    """An object to read a single text file from cache postition

    Parameters
    ----------
    name : |str|
        An absolute or relative path to the text file.
    offset : |int|, optional
        The file position of the last line read on the last interaction
    last_line : |str|, optional
        The value of the last line read on the last interaction
    """
    def __init__(self, name, offset=None, last_line=None):
        self.name = os.path.normpath(os.path.abspath(name))
        self.offset = None
        self.last_line = None
        self.fhandler = None
        self.set_position(offset, last_line)

    def get_position(self):
        return (self.offset, self.last_line)

    def set_position(self, offset=None, last_line=None):
        self.offset = offset or DEFAULT_POSITION[0]
        self.last_line = last_line or DEFAULT_POSITION[1]

    def __call__(self, offset=None, last_line=None):
        """Allow to set position inside with statement like

        >>> cutthelog = CutTheLog('/var/log/kern.log')
        >>> with cutthelog(offset=2605148, last_line='Feb 20 11:22:57 ...') as line_iter:
        ...     print(*line_iter, sep='')
        """
        self.set_position(offset, last_line)
        return self

    def __enter__(self):
        """Open the file and check if the position is correct

        If position is wrong reset it to the start of the file
        Return iterator over unseen lines"""
        fhandler = open(self.name, 'rb')
        offset, last_line = self.get_position()
        try:
            fhandler.seek(offset)
            line = next(fhandler)
            if line.rstrip(EOL) != last_line.rstrip(EOL):
                raise StopIteration
        except (IOError, StopIteration):
            fhandler.seek(0)
            self.set_position()
        self.fhandler = fhandler
        return iter(self)

    def is_file_opened(self):
        return self.fhandler is not None and not self.fhandler.closed

    def __exit__(self, exc_type, exc_value, traceback):
        """Close the file"""
        if self.is_file_opened():
            self.fhandler.close()

    def __iter__(self):
        """Iterator through lines of the file"""
        if not self.is_file_opened():
            return
        offset, last_line = self.get_position()
        offset_change = len(last_line)
        for line in self.fhandler:
            offset += offset_change
            self.set_position(offset, line)
            yield line
            offset_change = len(line)

    def get_eof_position(self):
        """Return offset and value of the last line without reading of the whole file"""
        chunk_size = 512
        last_line_chunks = []
        with open(self.name, 'rb') as fhandler:
            fhandler.seek(0, os.SEEK_END)
            offset = fhandler.tell()
            while offset > 0:
                step = min(chunk_size, offset)
                offset -= step
                fhandler.seek(offset, os.SEEK_SET)
                chunk = fhandler.read(step)
                start, end = (None, None) if last_line_chunks else (0, step - 1)
                last_line_pos = chunk.rfind(EOL, start, end) + 1
                if last_line_pos > 0:
                    offset += last_line_pos
                    last_line_chunks.append(chunk[last_line_pos:])
                    break
                last_line_chunks.append(chunk)
        return (offset, b''.join(reversed(last_line_chunks)))

    def _get_cache_props(self, delimiter):
        delimiter = delimiter or CACHE_DELIMITER
        return (self.name.encode() + delimiter.encode(), delimiter.encode())

    def set_position_from_cache(self, cache_file, delimiter=None):
        """Set file position from cache

        If there is no file record in the cache object position doesn't change
        A cache record of a file looks like
        <normalized absolute file path><delimiter><offset value><delimiter><last line value>

        There is no need to parse every cache line so we search only the required one
        and don't use the csv module

        Parameters
        ----------
        cache_file : |str|
            An path of cache file
        delimiter : |str|, optional
            An delimiter using by cache record

        Raises
        ------
        `CutthelogCacheError`
            On failed cache reading or malformed cache record for the file
        """
        file_prefix, delimiter = self._get_cache_props(delimiter)
        try:
            with open(cache_file, 'rb') as fhandler:
                line_iter = ((index, line) for index, line in enumerate(fhandler)
                             if line.startswith(file_prefix))
                index, line = next(line_iter, (None, None))
                if line is not None:
                    splitted_line = line.split(delimiter, 2)
                    if len(splitted_line) == 3:
                        try:
                            self.set_position(int(splitted_line[1]), splitted_line[2])
                        except ValueError:
                            msg = 'Bad offset {} in line #{}'.format(splitted_line[1], index)
                            raise CutthelogCacheError(msg)
                    else:
                        msg = 'Malformed cache line #{}: {}'.format(index, line.rstrip())
                        raise CutthelogCacheError(msg)
        except EnvironmentError as err:
            raise CutthelogCacheError('Failed to read cache: ' + str(err))

    def save_to_cache(self, cache_file, delimiter=None):
        """Save position of the file to cache

        At first the file record is written to temporary file, then records of other files are
        appended and finally the temporary file is copyed to the original cache path
        As a result records of the last read file are stored at the start of the cache so they are
        found faster on the next run

        Parameters
        ----------
        cache_file : |str|
            An path of cache file
        delimiter : |str|, optional
            An delimiter using by cache record

        Raises
        ------
        `CutthelogCacheError`
            On failed cache reading or malformed cache record for the file
        """
        file_prefix, delimiter = self._get_cache_props(delimiter)
        offset, last_line = self.get_position()
        try:
            with tempfile.NamedTemporaryFile(mode='wb') as fhandler:
                fhandler.write(self.name.encode())
                fhandler.write(delimiter)
                fhandler.write(str(offset).encode())
                fhandler.write(delimiter)
                fhandler.write(last_line)
                if not last_line.endswith(EOL):
                    fhandler.write(EOL)
                try:
                    with open(cache_file, 'rb') as source_fhandler:
                        for line in source_fhandler:
                            if not line.startswith(file_prefix):
                                fhandler.write(line)
                except EnvironmentError:
                    pass
                fhandler.flush()
                shutil.copyfile(fhandler.name, cache_file)
        except EnvironmentError as err:
            msg = 'Failed to save cache: ' + str(err)
            raise CutthelogCacheError(msg)


def argument_parsing():
    parser = argparse.ArgumentParser(description=__doc__)
    main_group = parser.add_mutually_exclusive_group(required=True)
    main_group.add_argument('logfile', help=HELPS['logfile'], nargs='?')
    main_group.add_argument('-V', '--version', help=HELPS['version'], action='store_true')
    parser.add_argument('-c', '--cache-file', help=HELPS['cache_file'])
    parser.add_argument('--cache-delimiter', help=HELPS['cache_delimiter'],
                        default=CACHE_DELIMITER)
    parser.add_argument('-v', '--verbose', help=HELPS['verbose'], action='store_true')
    args = parser.parse_args()
    if args.cache_file is None:
        home = os.getenv('USERPROFILE' if os.name == 'nt' else 'HOME', '/')
        home_cache = os.path.join(home, CACHE_FILENAME)
        args.cache_file = home_cache if os.access(home, os.R_OK | os.W_OK) else CACHE_FILENAME
    return args


def main():
    """The cutthelog command line utility

    It uses the basic function `CutTheLog` object. See description in README.rst
    """
    args = argument_parsing()
    if args.version:
        print(__version__)
        return 0
    lvl = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(stream=sys.stderr, level=lvl, format=LOG_FORMAT)
    if not os.path.isfile(args.logfile):
        logging.error('File "%s" not found', args.logfile)
        return 2
    if not os.access(args.logfile, os.R_OK):
        logging.error('No permission to read "%s"', args.logfile)
        return 2
    cutthelog = CutTheLog(args.logfile)
    if os.path.isfile(args.cache_file):
        try:
            cutthelog.set_position_from_cache(args.cache_file, delimiter=args.cache_delimiter)
        except CutthelogCacheError as err:
            logging.error(err)
            return 4
    initial_position = cutthelog.get_position()
    try:
        with cutthelog as line_iter:
            for line in line_iter:
                sys.stdout.buffer.write(line)
    except EnvironmentError as err:
        logging.error('Failed to read file: %s', err)
        return 3
    if cutthelog.get_position() != initial_position:
        try:
            cutthelog.save_to_cache(args.cache_file, delimiter=args.cache_delimiter)
        except CutthelogCacheError as err:
            logging.error(err)
            return 4
    return 0


if __name__ == '__main__':
    sys.exit(main())
