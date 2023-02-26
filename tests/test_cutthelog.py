# -*- coding: utf-8 -*-


import os
import shlex
import shutil
import subprocess
import tempfile
import unittest

import cutthelog as ctl

DATADIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data'))
CACHE_FILE = os.path.join(DATADIR, 'cache')
TEST_POSITIONS = (ctl.DEFAULT_POSITION, (10, b'abc'), (11111, b'xyz'))
NAME = 'empty'
ONE_LINE_NAME = 'one_line'
TWO_LINES_NAME = 'two_lines'
THREE_LINES_NAME = 'three_lines'
LONG_LINE_NAME = 'long_line'
TWO_LONG_LINES_NAME = 'two_long_lines'
LONG_LINE = b''.join(str(i).encode() for i in range(1, 501)) + ctl.EOL
LINES = (b'Hello, world!\n', b'Bye, world\n', b'Hello again')
ONE_LINE_POSITION = (0, LINES[0])
TWO_LINES_POSITION = (len(LINES[0]), LINES[1])
THREE_LINES_POSITION = (len(LINES[0]) + len(LINES[1]), LINES[2])


with open(CACHE_FILE, 'rb') as cache_handler:
    CACHE_LINES = list(cache_handler)
CACHE_CONTENT = b''.join(CACHE_LINES)


def get_data_file_path(filename):
    return os.path.join(DATADIR, filename)


def get_object(path=NAME, offset=None, last_line=None):
    filepath = get_data_file_path(path)
    return ctl.CutTheLog(filepath, offset, last_line)


class TestClass(unittest.TestCase):
    def test_init(self):
        obj = get_object()
        self.assertEqual(obj.path, get_data_file_path(NAME))
        self.assertEqual(obj.offset, ctl.DEFAULT_POSITION[0])
        self.assertEqual(obj.last_line, ctl.DEFAULT_POSITION[1])
        self.assertIsNone(obj.fhandler)
        obj = get_object(offset=TWO_LINES_POSITION[0], last_line=TWO_LINES_POSITION[1])
        self.assertEqual(obj.offset, TWO_LINES_POSITION[0])
        self.assertEqual(obj.last_line, TWO_LINES_POSITION[1])
        self.assertIsNone(obj.fhandler)

    def test_get_set_position(self):
        obj = get_object()
        self.assertEqual(obj.get_position(), ctl.DEFAULT_POSITION)
        obj.set_position()
        self.assertEqual(obj.get_position(), ctl.DEFAULT_POSITION)
        for pos in TEST_POSITIONS:
            obj.set_position(*pos)
            self.assertEqual(obj.get_position(), pos)
        obj.set_position()
        self.assertEqual(obj.get_position(), ctl.DEFAULT_POSITION)

    def test_call(self):
        obj = get_object()
        obj()
        self.assertEqual(obj.get_position(), ctl.DEFAULT_POSITION)
        for pos in TEST_POSITIONS:
            obj(*pos)
            self.assertEqual(obj.get_position(), pos)
        obj()
        self.assertEqual(obj.get_position(), ctl.DEFAULT_POSITION)

    def test_iter(self):
        obj = get_object()
        with self.assertRaises(StopIteration):
            next(iter(obj))
        with obj as line_iter:
            self.assertIs(iter(line_iter), line_iter)

    def test_with_statement(self):
        obj = get_object()
        with obj as line_iter:
            self.assertEqual(obj.get_position(), ctl.DEFAULT_POSITION)
            self.assertIsNotNone(obj.fhandler)
            self.assertFalse(obj.fhandler.closed)
            with self.assertRaises(StopIteration):
                next(line_iter)
        self.assertEqual(obj.get_position(), ctl.DEFAULT_POSITION)
        self.assertTrue(obj.fhandler.closed)

    def test_one_line_file(self):
        obj = get_object(ONE_LINE_NAME)
        self.assertEqual(obj.get_position(), ctl.DEFAULT_POSITION)
        with obj as line_iter:
            self.assertEqual(next(line_iter), LINES[0])
            with self.assertRaises(StopIteration):
                next(line_iter)
        self.assertEqual(obj.get_position(), ONE_LINE_POSITION)
        with obj as line_iter:
            with self.assertRaises(StopIteration):
                next(line_iter)
        self.assertEqual(obj.get_position(), ONE_LINE_POSITION)

    def test_two_lines_file(self):
        obj = get_object(TWO_LINES_NAME)
        self.assertEqual(obj.get_position(), ctl.DEFAULT_POSITION)
        with obj as line_iter:
            self.assertEqual(tuple(line_iter), LINES[:2])
        self.assertEqual(obj.get_position(), TWO_LINES_POSITION)
        with obj as line_iter:
            with self.assertRaises(StopIteration):
                next(line_iter)
        self.assertEqual(obj.get_position(), TWO_LINES_POSITION)

    def test_with_statement_with_valid_position(self):
        obj = get_object(TWO_LINES_NAME)
        with obj(*TWO_LINES_POSITION) as line_iter:
            self.assertEqual(obj.get_position(), TWO_LINES_POSITION)
            self.assertIsNotNone(obj.fhandler)
            self.assertFalse(obj.fhandler.closed)
            with self.assertRaises(StopIteration):
                next(line_iter)
        self.assertEqual(obj.get_position(), TWO_LINES_POSITION)
        self.assertTrue(obj.fhandler.closed)

    def test_with_statement_with_invalid_last_line(self):
        obj = get_object(TWO_LINES_NAME)
        with obj(offset=TWO_LINES_POSITION[0], last_line=b'abc\n') as line_iter:
            self.assertEqual(obj.get_position(), ctl.DEFAULT_POSITION)
            self.assertEqual(next(line_iter), LINES[0])

    def test_with_statement_with_invalid_position_value(self):
        obj = get_object(TWO_LINES_NAME)
        with obj(offset=4, last_line=ONE_LINE_POSITION[1]) as line_iter:
            self.assertEqual(obj.get_position(), ctl.DEFAULT_POSITION)
            self.assertEqual(next(line_iter), LINES[0])

    def test_with_statement_with_out_of_file_position_value(self):
        obj = get_object(TWO_LINES_NAME)
        with obj(offset=1000, last_line=ONE_LINE_POSITION[1]) as line_iter:
            self.assertEqual(obj.get_position(), ctl.DEFAULT_POSITION)
            self.assertEqual(next(line_iter), LINES[0])

    def test_with_statement_with_end_of_file_position_value(self):
        obj = get_object(TWO_LINES_NAME)
        with obj(offset=THREE_LINES_POSITION[0], last_line='') as line_iter:
            self.assertEqual(obj.get_position(), ctl.DEFAULT_POSITION)
            self.assertEqual(next(line_iter), LINES[0])

    def test_two_lines_file_separated_read(self):
        obj = get_object(TWO_LINES_NAME)
        with obj as line_iter:
            self.assertEqual(next(line_iter), LINES[0])
        self.assertEqual(obj.get_position(), ONE_LINE_POSITION)
        with obj as line_iter:
            self.assertEqual(next(line_iter), LINES[1])
        self.assertEqual(obj.get_position(), TWO_LINES_POSITION)

    def test_file_witout_eol_before_eof(self):
        obj = get_object(THREE_LINES_NAME)
        with obj as line_iter:
            self.assertEqual(tuple(line_iter), LINES[:3])
        self.assertEqual(obj.get_position(), THREE_LINES_POSITION)

    def test_position_in_file_witout_eol_before_eof(self):
        obj = get_object(THREE_LINES_NAME)
        with obj(*THREE_LINES_POSITION) as line_iter:
            self.assertEqual(obj.get_position(), THREE_LINES_POSITION)
            with self.assertRaises(StopIteration):
                next(line_iter)
        self.assertEqual(obj.get_position(), THREE_LINES_POSITION)

    def test_get_eof_position(self):
        obj = get_object(NAME)
        self.assertEqual(obj.get_eof_position(), ctl.DEFAULT_POSITION)
        obj = get_object(ONE_LINE_NAME)
        self.assertEqual(obj.get_eof_position(), ONE_LINE_POSITION)
        obj = get_object(TWO_LINES_NAME)
        self.assertEqual(obj.get_eof_position(), TWO_LINES_POSITION)
        obj = get_object(THREE_LINES_NAME)
        self.assertEqual(obj.get_eof_position(), THREE_LINES_POSITION)

    def test_get_eof_position_on_long_lines(self):
        obj = get_object(LONG_LINE_NAME)
        self.assertEqual(obj.get_eof_position(), (0, LONG_LINE))
        obj = get_object(TWO_LONG_LINES_NAME)
        self.assertEqual(obj.get_eof_position(), (len(LONG_LINE), LONG_LINE[1:]))

    def test_non_existing_files(self):
        obj = get_object('no-such-file')
        with self.assertRaises(IOError):
            with obj:
                pass
        obj = get_object('no-such-dir/no-such-file')
        with self.assertRaises(IOError):
            with obj:
                pass

    def test_set_position_from_cache(self):
        def check(filename, check_res, delimiter=None):
            obj = get_object(filename)
            obj.set_position_from_cache(CACHE_FILE, delimiter=delimiter)
            self.assertEqual(obj.get_position(), check_res)
        check('/root/hello', (50, b'Hello, world\n'))
        check('/root/hello.2', (100, b'Hello, world!\n'))
        check('/root/hello.3', (200, b'Hello##world!\n'))
        check('/root/no_such_file_in_cache', ctl.DEFAULT_POSITION)
        with self.assertRaises(ctl.CutthelogCacheError):
            check('/root/bad_format', ctl.DEFAULT_POSITION)
        with self.assertRaises(ctl.CutthelogCacheError):
            check('/root/bad_offset', ctl.DEFAULT_POSITION)
        check('/root/unable_to_find', ctl.DEFAULT_POSITION)
        check('/root/hello', (60, b'Hello, world\n'), delimiter='%%')

    def test_save_to_cache(self):
        def check(filename, position, last_line, cache_lines, delimiter=None):
            obj = ctl.CutTheLog(filename, position, last_line)
            with tempfile.NamedTemporaryFile(mode='rb') as fhandler:
                shutil.copyfile(CACHE_FILE, fhandler.name)
                obj.save_to_cache(fhandler.name, delimiter=delimiter)
                self.assertEqual(fhandler.read(), b''.join(cache_lines))
        check('/root/hello.2', 100, b'Hello, world!\n', CACHE_LINES)
        check('/root/hello.2', 100, b'Hello, world!', CACHE_LINES)
        cache_lines = CACHE_LINES[2:3] + CACHE_LINES[:2] + CACHE_LINES[3:]
        check('/root/hello', 50, b'Hello, world', cache_lines)
        cache_lines = [b'/root/unable_to_find##10##aaa\n'] + CACHE_LINES
        check('/root/unable_to_find', 10, b'aaa', cache_lines)
        cache_lines = [b'/root/hello%%60%%Hello, world\n'] + CACHE_LINES[:-1]
        check('/root/hello', 60, b'Hello, world', cache_lines, delimiter='%%')
        cache_lines = [b'/root/bad_offset##88##Good line\n'] + CACHE_LINES[:4] + CACHE_LINES[5:]
        check('/root/bad_offset', 88, b'Good line\n', cache_lines)


class TestUtil(unittest.TestCase):
    cmd_tmpl = 'python3 ./cutthelog.py -c {cache_file} {filename}'

    def setUp(self):
        file_id, self.cache_file = tempfile.mkstemp(prefix='cutthelog_cache_')
        os.close(file_id)

    def tearDown(self):
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)

    def run_util(self, filename, cache_file=None):
        filename = get_data_file_path(filename)
        cache_file = cache_file or self.cache_file
        cmd = self.cmd_tmpl.format(cache_file=cache_file, filename=filename)
        proc = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        return (proc.returncode, stdout, stderr)

    def check(self, filename, returncode=0, stdout='', stderr='', cache='', cache_file=None):
        real_rc, real_stdout, real_stderr = self.run_util(filename, cache_file=cache_file)
        stdout = stdout if isinstance(stdout, bytes) else stdout.encode()
        stderr = stderr if isinstance(stderr, bytes) else stderr.encode()
        self.assertEqual(real_stdout, stdout)
        self.assertEqual(real_stderr.rstrip(ctl.EOL), stderr)
        self.assertEqual(real_rc, returncode)
        if cache is not None:
            with open(cache_file or self.cache_file, 'rb') as fhanlder:
                self.assertEqual(fhanlder.read().decode(), cache)

    def test_empty_file(self):
        self.check('empty')

    def test_nonexistant_file(self):
        filename = 'no-such-file'
        stderr = 'ERROR: ' + ctl.NOT_FOUND % get_data_file_path(filename)
        self.check(filename, returncode=66, stderr=stderr)

    def test_no_perm_file(self):
        with tempfile.NamedTemporaryFile() as fhandler:
            filename = fhandler.name
            os.chmod(filename, 0o000)
            stderr = 'ERROR: ' + ctl.NO_PERMISSION % ('read', filename)
            self.check(filename, returncode=77, stderr=stderr)

    def test_one_line_file(self):
        self.check('one_line', stdout=LINES[0], cache=None)

    def test_cache_in_nonexistant_directory(self):
        cache_dir = '/no-such-dir'
        cache_file = os.path.join(cache_dir, 'no-such-file')
        stderr = 'ERROR: ' + ctl.NOT_FOUND % cache_dir
        self.check('one_line', returncode=74, cache_file=cache_file, stderr=stderr, cache=None)

    def test_cache_in_no_permission_directory(self):
        cache_dir = tempfile.mkdtemp()
        os.chmod(cache_dir, 0o400)
        cache_file = os.path.join(cache_dir, 'no-such-file')
        stderr = 'ERROR: ' + ctl.NO_PERMISSION % ('read/write', cache_dir)
        self.check('one_line', returncode=77, cache_file=cache_file, stderr=stderr, cache=None)
        os.chmod(cache_dir, 0o700)
        os.rmdir(cache_dir)

    def test_no_write_perm_cache_file(self):
        with tempfile.NamedTemporaryFile() as fhandler:
            cache_file = fhandler.name
            os.chmod(cache_file, 0o400)
            stderr = 'ERROR: ' + ctl.NO_PERMISSION % ('read/write', cache_file)
            self.check('one_line', returncode=77, cache_file=cache_file, stderr=stderr, cache=None)


class TestUtilWithPython2(unittest.TestCase):
    cmd_tmpl = 'python2 ./cutthelog.py -c {cache_file} {filename}'


if __name__ == '__main__':
    unittest.main()
