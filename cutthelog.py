#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from __future__ import print_function

import os
import sys
import logging
import argparse


DEFAULT_POSITION = (0, '')
DESCRIPTION = ''
HELPS = {
    'logfile': '',
    'cache_file': '',
    'offset': '',
    'last_line': '',
    'cache_delimiter': '',
    'verbose': 'enable verbose mode',
}
LOG_FORMAT = '%(asctime)s %(levelname)s: %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
CACHE_DELIMITER = '##'


class CutTheLog(object):
    """Class to parse log file"""
    def __init__(self, name, offset=None, last_line=None):
        """Initialize object to work with log file"""
        self.name = name
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


def argument_parsing():
    """Parse and return command line arguments"""
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument('logfile', help=HELPS['logfile'], nargs='+')
    parser.add_argument('-c', '--cache-file', help=HELPS['cache_file'])
    parser.add_argument('--cache-delimiter', help=HELPS['cache_delimiter'],
                        default=CACHE_DELIMITER)
    parser.add_argument('--offset', help=HELPS['offset'], type=int)
    parser.add_argument('--last-line', help=HELPS['last_line'])
    parser.add_argument('-v', '--verbose', help=HELPS['verbose'], action='store_true')
    args = parser.parse_args()
    if args.cache_file is None:
        workdir = os.getenv('HOME') or os.getcwd()
        args.cache_file = os.path.join(workdir, '.cutthelog')
    return args


def parse_cache(cache_file, delimiter):
    """Open cache file and return content as content as a dict"""
    result = {}
    if not os.path.isfile(cache_file):
        return result
    try:
        with open(cache_file, 'r') as fh:
            for index, line in enumerate(fh):
                splited_line = line.split(delimiter, 3)
                if len(splited_line) != 3:
                    logging.warning('Malformed cache line #%d: %s', index, line.rstrip())
                    continue
                filename, offset, last_line = splited_line
                try:
                    offset = int(offset)
                except ValueError:
                    logging.warning('Malformed offset value %s in line #%d', offset, index)
                    continue
                result[filename] = (offset, last_line)
    except EnvironmentError as err:
        logging.warning('Failed to read cache: %s', err)
    return result


def save_cache(cache_file, cache, delimiter):
    """Save cache dictionary to cache file"""
    try:
        with open(cache_file, 'w+') as fh:
            for filename, pos_tuple in cache.items():
                offset, last_line = pos_tuple
                print(filename, offset, last_line, sep=delimiter, file=fh,
                      end='' if last_line.endswith('\n') else '\n')
    except EnvironmentError as err:
        logging.error('Failed to save cache: %s', err)


def main():
    """
    Main function of command line utility
    """
    args = argument_parsing()
    lvl = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(stream=sys.stderr, level=lvl, format=LOG_FORMAT, datefmt=DATE_FORMAT)
    cache = {}
    offset, last_line = args.offset, args.last_line
    use_cache = offset is None or last_line is None
    if use_cache:
        cache = parse_cache(args.cache_file, args.cache_delimiter)
    for logfile in args.logfile:
        if not os.path.isfile(logfile):
            logging.warning('Log file %s not found', logfile)
            continue
        filename = os.path.normpath(os.path.abspath(logfile))
        if use_cache:
            offset, last_line = cache.get(filename, (0, ''))
        cutthelog = CutTheLog(filename)
        try:
            with cutthelog(offset=offset, last_line=last_line) as fh:
                for line in fh:
                    print(line, end='')
        except EnvironmentError as err:
            logging.error('Error reading log: %s', err)
            continue
        cache[filename] = (cutthelog.offset, cutthelog.last_line)
    if use_cache:
        save_cache(args.cache_file, cache, args.cache_delimiter)


if __name__ == '__main__':
    main()
