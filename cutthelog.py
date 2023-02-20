#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from __future__ import print_function

import argparse
import logging
import os
import shutil
import sys
import tempfile

VERSION = (1, 0, 0)
__version__ = '.'.join(map(str, VERSION))
DEFAULT_POSITION = (0, '')
DESCRIPTION = ''
HELPS = {
    'logfile': '',
    'cache_file': '',
    'offset': '',
    'last_line': '',
    'cache_delimiter': '',
    'verbose': 'enable verbose mode',
    'version': 'print utility version and exit',
}
LOG_FORMAT = '%(asctime)s %(levelname)s: %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
CACHE_DELIMITER = '##'
CACHE_FILENAME = '.cutthelog'


class CutthelogError(Exception):
    """General module exception"""


class CutthelogCacheError(CutthelogError):
    """Error on cache interaction"""


class CutTheLog:
    """Class to parse log file"""
    def __init__(self, name, offset=None, last_line=None):
        """Initialize object to work with log file"""
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
        """Method to run into the with statement"""
        self.set_position(offset, last_line)
        return self

    def __enter__(self):
        """Return iterator of lines of the log file"""
        fhandler = open(self.name, 'r')
        offset, last_line = self.get_position()
        try:
            fhandler.seek(offset)
            line = next(fhandler)
            if line.rstrip('\n') != last_line.rstrip('\n'):
                raise StopIteration
        except (IOError, StopIteration):
            fhandler.seek(0)
            self.set_position()
        self.fhandler = fhandler
        return iter(self)

    def _is_file_opened(self):
        return self.fhandler is not None and not self.fhandler.closed

    def __exit__(self, exc_type, exc_value, traceback):
        """Close the log file"""
        if self._is_file_opened():
            self.fhandler.close()

    def __iter__(self):
        """Iterator through lines of the log file"""
        if not self._is_file_opened():
            return
        offset, last_line = self.get_position()
        offset_change = len(last_line)
        for line in self.fhandler:
            offset += offset_change
            self.set_position(offset, line)
            yield line
            offset_change = len(line)

    def get_eof_position(self):
        """Return offset and last line without the whole file reading"""
        chunk_size = 512
        last_line_chunks = []
        with open(self.name, 'r') as fhandler:
            fhandler.seek(0, os.SEEK_END)
            offset = fhandler.tell()
            while offset > 0:
                step = min(chunk_size, offset)
                offset -= step
                fhandler.seek(offset, os.SEEK_SET)
                chunk = fhandler.read(step)
                start, end = (None, None) if last_line_chunks else (0, step - 1)
                last_line_pos = chunk.rfind('\n', start, end) + 1
                if last_line_pos > 0:
                    offset += last_line_pos
                    last_line_chunks.append(chunk[last_line_pos:])
                    break
                last_line_chunks.append(chunk)
        return (offset, ''.join(reversed(last_line_chunks)))

    def _get_cache_props(self, delimiter):
        delimiter = delimiter or CACHE_DELIMITER
        return (self.name + delimiter, delimiter)

    def set_position_from_cache(self, cache_file, delimiter=None):
        file_prefix, delimiter = self._get_cache_props(delimiter)
        try:
            with open(cache_file, 'r') as fhandler:
                line_iter = ((index, line) for index, line in enumerate(fhandler)
                             if line.startswith(file_prefix))
                index, line = next(line_iter, (None, None))
                if line is not None:
                    splitted_line = line.split(delimiter, 2)
                    if len(splitted_line) == 3:
                        try:
                            self.set_position(int(splitted_line[1]), splitted_line[2])
                        except ValueError:
                            msg = 'Bad offset {0} in line #{1}'.format(splitted_line[1], index)
                            raise CutthelogCacheError(msg)
                    else:
                        msg = 'Malformed cache line #{0}: {1}'.format(index, line.rstrip())
                        raise CutthelogCacheError(msg)
        except (EnvironmentError, UnicodeDecodeError) as err:
            raise CutthelogCacheError('Failed to read cache: ' + str(err))

    def save_to_cache(self, cache_file, delimiter=None):
        """Save cache dictionary to cache file"""
        file_prefix, delimiter = self._get_cache_props(delimiter)
        offset, last_line = self.get_position()
        try:
            with tempfile.NamedTemporaryFile(mode='w') as fhandler:
                print(self.name, offset, last_line, sep=delimiter, file=fhandler,
                      end='' if last_line.endswith('\n') else '\n')
                with open(cache_file, 'r') as source_fhandler:
                    for line in source_fhandler:
                        if not line.startswith(file_prefix):
                            print(line, file=fhandler, end='')
                fhandler.flush()
                shutil.copyfile(fhandler.name, cache_file)
        except (EnvironmentError, UnicodeEncodeError) as err:
            msg = 'Failed to save cache: ' + str(err)
            raise CutthelogCacheError(msg)


def argument_parsing():
    """Parse and return command line arguments"""
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    main_group = parser.add_mutually_exclusive_group(required=True)
    main_group.add_argument('logfile', help=HELPS['logfile'], nargs='?')
    main_group.add_argument('-V', '--version', help=HELPS['version'], action='store_true')
    parser.add_argument('-c', '--cache-file', help=HELPS['cache_file'])
    parser.add_argument('--cache-delimiter', help=HELPS['cache_delimiter'],
                        default=CACHE_DELIMITER)
    parser.add_argument('--offset', help=HELPS['offset'], type=int)
    parser.add_argument('--last-line', help=HELPS['last_line'])
    parser.add_argument('-v', '--verbose', help=HELPS['verbose'], action='store_true')
    args = parser.parse_args()
    if args.cache_file is None:
        workdir = os.getcwd() if os.path.exists(CACHE_FILENAME) else os.getenv('HOME')
        args.cache_file = os.path.join(workdir, CACHE_FILENAME)
    return args


def main():
    """
    Main function of command line utility
    """
    args = argument_parsing()
    if args.version:
        print(__version__)
        return 0
    lvl = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(stream=sys.stderr, level=lvl, format=LOG_FORMAT, datefmt=DATE_FORMAT)
    if not os.path.isfile(args.logfile):
        logging.error('Log file %s not found', args.logfile)
        return 2
    cutthelog = CutTheLog(args.logfile, args.offset, args.last_line)
    use_cache = args.offset is None or args.last_line is None
    if use_cache:
        try:
            cutthelog.set_position_from_cache(args.cache_file, delimiter=args.cache_delimiter)
        except CutthelogCacheError as err:
            logging.error(err)
            return 4
    cached_position = cutthelog.get_position()
    try:
        with cutthelog as line_iter:
            for line in line_iter:
                print(line, end='')
    except (EnvironmentError, UnicodeDecodeError) as err:
        logging.error('Error reading file: %s', err)
        return 3
    if use_cache and cutthelog.get_position() != cached_position:
        try:
            cutthelog.save_to_cache(args.cache_file, delimiter=args.cache_delimiter)
        except CutthelogCacheError as err:
            logging.error(err)
            return 4
    return 0


if __name__ == '__main__':
    sys.exit(main())
