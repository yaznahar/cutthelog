#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from __future__ import print_function

import os
import sys
import shutil
import logging
import tempfile
import argparse


VERSION = (1, 0)
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


class CutTheLog(object):
    """Class to parse log file"""
    def __init__(self, name, offset=None, last_line=None):
        """Initialize object to work with log file"""
        self.name = os.path.normpath(os.path.abspath(name))
        self.offset = None
        self.last_line = None
        self.fh = None
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
        fh = open(self.name, 'r')
        offset, last_line = self.get_position()
        try:
            fh.seek(offset)
            line = next(fh)
            if line.rstrip('\n') != last_line.rstrip('\n'):
                raise StopIteration
        except (IOError, StopIteration):
            fh.seek(0)
            self.set_position()
        self.fh = fh
        return iter(self)

    def __exit__(self, exc_type, exc_value, traceback):
        """Close the log file"""
        if self.fh is not None and not self.fh.closed:
            self.fh.close()

    def __iter__(self):
        """Iterator through lines of the log file"""
        if self.fh is None or self.fh.closed:
            return
        offset, last_line = self.get_position()
        offset_change = len(last_line)
        for line in self.fh:
            offset += offset_change
            self.set_position(offset, line)
            yield line
            offset_change = len(line)

    def get_eof_position(self):
        """Return offset and last line without the whole file reading"""
        chunk_size = 512
        last_line_chunks = []
        with open(self.name, 'r') as fh:
            fh.seek(0, os.SEEK_END)
            offset = fh.tell()
            while offset > 0:
                step = min(chunk_size, offset)
                offset -= step
                fh.seek(offset, os.SEEK_SET)
                chunk = fh.read(step)
                start, end = (None, None) if last_line_chunks else (0, step - 1)
                last_line_pos = chunk.rfind('\n', start, end) + 1
                if last_line_pos > 0:
                    offset += last_line_pos
                    last_line_chunks.append(chunk[last_line_pos:])
                    break
                else:
                    last_line_chunks.append(chunk)
        return (offset, ''.join(reversed(last_line_chunks)))

    def _get_cache_props(self, delimiter):
        delimiter = delimiter or CACHE_DELIMITER
        return (self.name + delimiter, delimiter)

    def set_position_from_cache(self, cache_file, delimiter=None):
        file_prefix, delimiter = self._get_cache_props(delimiter)
        try:
            with open(cache_file, 'r') as fh:
                line_iter = ((index, line) for index, line in enumerate(fh) if line.startswith(file_prefix))
                index, line = next(line_iter, (None, None))
                if line is not None:
                    splitted_line = line.split(delimiter, 2)
                    if len(splitted_line) == 3:
                        try:
                            self.set_position(int(splitted_line[1]), splitted_line[2])
                        except ValueError:
                            logging.warning('Malformed offset value %s in line #%d', splitted_line[1], index)
                    else:
                        logging.warning('Malformed cache line #%d: %s', index, line.rstrip())
        except (EnvironmentError, UnicodeDecodeError) as err:
            logging.warning('Failed to read cache: %s', err)

    def save_to_cache(self, cache_file, delimiter=None):
        """Save cache dictionary to cache file"""
        file_prefix, delimiter = self._get_cache_props(delimiter)
        offset, last_line = self.get_position()
        try:
            with tempfile.NamedTemporaryFile(mode='w') as fh:
                print(self.name, offset, last_line, sep=delimiter, file=fh,
                      end='' if last_line.endswith('\n') else '\n')
                try:
                    with open(cache_file, 'r') as source_fh:
                        for line in source_fh:
                            if not line.startswith(file_prefix):
                                print(line, file=fh, end='')
                except (EnvironmentError, UnicodeEncodeError):
                    pass
                fh.flush()
                shutil.copyfile(fh.name, cache_file)
        except (EnvironmentError, UnicodeEncodeError) as err:
            logging.error('Failed to save cache: %s', err)


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
        sys.exit(0)
    lvl = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(stream=sys.stderr, level=lvl, format=LOG_FORMAT, datefmt=DATE_FORMAT)
    if not os.path.isfile(args.logfile):
        logging.warning('Log file %s not found', args.logfile)
        return
    cutthelog = CutTheLog(args.logfile, args.offset, args.last_line)
    use_cache = args.offset is None or args.last_line is None
    if use_cache:
        cutthelog.set_position_from_cache(args.cache_file, delimiter=args.cache_delimiter)
    cached_position = cutthelog.get_position()
    try:
        with cutthelog as line_iter:
            for line in line_iter:
                print(line, end='')
    except (EnvironmentError, UnicodeDecodeError) as err:
        logging.error('Error reading file: %s', err)
    if use_cache and cutthelog.get_position() != cached_position:
        cutthelog.save_to_cache(args.cache_file, delimiter=args.cache_delimiter)


if __name__ == '__main__':
    main()
