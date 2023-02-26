#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Print an unseen tailing part of a log file"""


import argparse
import logging
import os
import shutil
import sys
import tempfile

VERSION = (0, 9, 2)
__version__ = '.'.join(map(str, VERSION))
DEFAULT_POSITION = (0, b'')
LOG_FORMAT = '%(levelname)s: %(message)s'
CACHE_DELIMITER = '##'
EOL = b'\n'
CACHE_FILENAME = '.cutthelog'
HELPS = {
    'logfile': 'path of a file to print',
    'cache_file': 'path of the cache file',
    'cache_delimiter': 'delimiter of cache record (by default "{}")'.format(CACHE_DELIMITER),
    'verbose': 'enable verbose mode',
    'version': 'print utility version and exit',
}
NOT_FOUND = 'File "%s" not found'
NO_PERMISSION = 'No permission to %s "%s"'


class CutthelogError(Exception):
    """General module exception"""


class CutthelogCacheError(CutthelogError):
    """Error of cache interaction"""


class CutTheLog:
    """A class to read a single file from cache postition"""

    def __init__(self, path, offset=None, last_line=None):
        """An object initilization

        Parameters
        ----------
        path : |str|
            An absolute or relative path of a file to read
        offset : |int|, optional
            The file position of the last line read on the last interaction
        last_line : |bytes|, optional
            The value of the last line read on the last interaction
        """
        self.path = os.path.normpath(os.path.abspath(path))
        self.offset = None
        self.last_line = None
        self.fhandler = None
        self.set_position(offset, last_line)

    def get_position(self):
        """Return position stored in the object"""
        return (self.offset, self.last_line)

    def set_position(self, offset=None, last_line=None):
        """Set internal object position or reset it without arguments"""
        self.offset = offset or DEFAULT_POSITION[0]
        self.last_line = last_line or DEFAULT_POSITION[1]

    def __call__(self, offset=None, last_line=None):
        """Allow to set position inside with statement like

        Parameters
        ----------
        offset : |int|, optional
            The file position of the last line read on the last interaction
        last_line : |bytes|, optional
            The value of the last line read on the last interaction

        Examples
        --------
        >>> cutthelog = CutTheLog('/var/log/kern.log')
        >>> with cutthelog(offset=2605148, last_line=b'Feb 20 11:22:57 ...') as line_iter:
        ...     for line in line_iter:
        ...         print(line.encode(), end='')
        """
        self.set_position(offset, last_line)
        return self

    def __enter__(self):
        """Open the file and check whether the position is correct

        If check fails and the position resets to the start of the file.
        Return iterator over unseen byte lines"""
        fhandler = open(self.path, 'rb')
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
        """Iterator over lines of the file

        It's intended only for using inside the __enter__ method
        when the file is opened"""
        if not self.is_file_opened():
            return
        offset_change = len(self.last_line)
        for line in self.fhandler:
            self.offset += offset_change
            self.last_line = line
            yield line
            offset_change = len(line)

    def get_eof_position(self):
        """Return offset and value of the last line without reading of the whole file

        Raises
        ------
        EnvironmentError
            On failed file opening or reading
        """
        chunk_size = 512
        last_line_chunks = []
        with open(self.path, 'rb') as fhandler:
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
        return (self.path.encode() + delimiter.encode(), delimiter.encode())

    def set_position_from_cache(self, cache_file, delimiter=None):
        """Set the internal position from cache file

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
                fhandler.write(self.path.encode())
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


def check_logfile(path):
    if not os.path.isfile(path):
        logging.error(NOT_FOUND, path)
        return 66
    if not os.access(path, os.R_OK):
        logging.error(NO_PERMISSION, 'read', path)
        return 77
    return 0


def check_cache_file(path):
    if os.path.isfile(path):
        if not os.access(path, os.R_OK | os.W_OK):
            logging.error(NO_PERMISSION, 'read/write', path)
            return 77
    else:
        cache_dir = os.path.dirname(path)
        if not os.path.isdir(cache_dir):
            logging.error(NOT_FOUND, cache_dir)
            return 74
        if not os.access(cache_dir, os.R_OK | os.W_OK):
            logging.error(NO_PERMISSION, 'read/write', cache_dir)
            return 77
        try:
            with open(path, 'wb'):
                pass
        except EnvironmentError as err:
            logging.error('Failed to create file: %s', err)
            return 74
    return 0


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
    returncode = check_logfile(args.logfile) or check_cache_file(args.cache_file)
    if returncode:
        return returncode
    cutthelog = CutTheLog(args.logfile)
    try:
        cutthelog.set_position_from_cache(args.cache_file, delimiter=args.cache_delimiter)
    except CutthelogCacheError as err:
        logging.error(err)
        return 74
    initial_position = cutthelog.get_position()
    try:
        with cutthelog as line_iter:
            stdout = sys.stdout.buffer if hasattr(sys.stdout, 'buffer') else sys.stdout
            stdout.writelines(line_iter)
    except EnvironmentError as err:
        logging.error('Failed to read file: %s', err)
        return 74
    if cutthelog.get_position() != initial_position:
        try:
            cutthelog.save_to_cache(args.cache_file, delimiter=args.cache_delimiter)
        except CutthelogCacheError as err:
            logging.error(err)
            return 74
    return 0


if __name__ == '__main__':
    sys.exit(main())
