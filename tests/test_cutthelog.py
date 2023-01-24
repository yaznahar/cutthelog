# -*- coding: utf-8 -*-


import os
import unittest


import cutthelog as ctl


DATADIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data'))
TEST_POSITIONS = (ctl.DEFAULT_POSITION, (10, 'abc'), (11111, 'xyz'))
NAME = 'empty'
ONE_LINE_NAME = 'one_line'
TWO_LINES_NAME = 'two_lines'
THREE_LINES_NAME = 'three_lines'
LONG_LINE_NAME = 'long_line'
TWO_LONG_LINES_NAME = 'two_long_lines'
LONG_LINE = ''.join(str(i) for i in range(1, 501)) + '\n'
LINES = ('Hello, world!\n', 'Bye, world\n', 'Hello again')
ONE_LINE_POSITION = (0, LINES[0])
TWO_LINES_POSITION = (len(LINES[0]), LINES[1])
THREE_LINES_POSITION = (len(LINES[0]) + len(LINES[1]), LINES[2])


class TestCutTheLog(unittest.TestCase):
    def get_object(self, name=NAME, offset=None, last_line=None):
        filename = os.path.join(DATADIR, name)
        return ctl.CutTheLog(filename, offset, last_line)

    def test_init(self):
        obj = self.get_object()
        self.assertEqual(obj.name, os.path.join(DATADIR, NAME))
        self.assertEqual(obj.offset, ctl.DEFAULT_POSITION[0])
        self.assertEqual(obj.last_line, ctl.DEFAULT_POSITION[1])
        self.assertIsNone(obj.fh)
        obj = self.get_object(offset=TWO_LINES_POSITION[0], last_line=TWO_LINES_POSITION[1])
        self.assertEqual(obj.offset, TWO_LINES_POSITION[0])
        self.assertEqual(obj.last_line, TWO_LINES_POSITION[1])
        self.assertIsNone(obj.fh)

    def test_get_set_position(self):
        obj = self.get_object()
        self.assertEqual(obj.get_position(), ctl.DEFAULT_POSITION)
        obj.set_position()
        self.assertEqual(obj.get_position(), ctl.DEFAULT_POSITION)
        for pos in TEST_POSITIONS:
            obj.set_position(*pos)
            self.assertEqual(obj.get_position(), pos)
        obj.set_position()
        self.assertEqual(obj.get_position(), ctl.DEFAULT_POSITION)

    def test_call(self):
        obj = self.get_object()
        obj()
        self.assertEqual(obj.get_position(), ctl.DEFAULT_POSITION)
        for pos in TEST_POSITIONS:
            obj(*pos)
            self.assertEqual(obj.get_position(), pos)
        obj()
        self.assertEqual(obj.get_position(), ctl.DEFAULT_POSITION)

    def test_iter(self):
        obj = self.get_object()
        with self.assertRaises(StopIteration):
            next(iter(obj))
        with obj as line_iter:
            self.assertIs(iter(line_iter), line_iter)

    def test_with_statement(self):
        obj = self.get_object()
        with obj as line_iter:
            self.assertEqual(obj.get_position(), ctl.DEFAULT_POSITION)
            self.assertIsNotNone(obj.fh)
            self.assertFalse(obj.fh.closed)
            with self.assertRaises(StopIteration):
                next(line_iter)
        self.assertEqual(obj.get_position(), ctl.DEFAULT_POSITION)
        self.assertTrue(obj.fh.closed)

    def test_one_line_file(self):
        obj = self.get_object(ONE_LINE_NAME)
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
        obj = self.get_object(TWO_LINES_NAME)
        self.assertEqual(obj.get_position(), ctl.DEFAULT_POSITION)
        with obj as line_iter:
            self.assertEqual(tuple(line_iter), LINES[:2])
        self.assertEqual(obj.get_position(), TWO_LINES_POSITION)
        with obj as line_iter:
            with self.assertRaises(StopIteration):
                next(line_iter)
        self.assertEqual(obj.get_position(), TWO_LINES_POSITION)

    def test_with_statement_with_valid_position(self):
        obj = self.get_object(TWO_LINES_NAME)
        with obj(*TWO_LINES_POSITION) as line_iter:
            self.assertEqual(obj.get_position(), TWO_LINES_POSITION)
            self.assertIsNotNone(obj.fh)
            self.assertFalse(obj.fh.closed)
            with self.assertRaises(StopIteration):
                next(line_iter)
        self.assertEqual(obj.get_position(), TWO_LINES_POSITION)
        self.assertTrue(obj.fh.closed)

    def test_with_statement_with_invalid_last_line(self):
        obj = self.get_object(TWO_LINES_NAME)
        with obj(offset=TWO_LINES_POSITION[0], last_line='abc\n') as line_iter:
            self.assertEqual(obj.get_position(), ctl.DEFAULT_POSITION)
            self.assertEqual(next(line_iter), LINES[0])

    def test_with_statement_with_invalid_position_value(self):
        obj = self.get_object(TWO_LINES_NAME)
        with obj(offset=4, last_line=ONE_LINE_POSITION[1]) as line_iter:
            self.assertEqual(obj.get_position(), ctl.DEFAULT_POSITION)
            self.assertEqual(next(line_iter), LINES[0])

    def test_with_statement_with_out_of_file_position_value(self):
        obj = self.get_object(TWO_LINES_NAME)
        with obj(offset=1000, last_line=ONE_LINE_POSITION[1]) as line_iter:
            self.assertEqual(obj.get_position(), ctl.DEFAULT_POSITION)
            self.assertEqual(next(line_iter), LINES[0])

    def test_with_statement_with_end_of_file_position_value(self):
        obj = self.get_object(TWO_LINES_NAME)
        with obj(offset=THREE_LINES_POSITION[0], last_line='') as line_iter:
            self.assertEqual(obj.get_position(), ctl.DEFAULT_POSITION)
            self.assertEqual(next(line_iter), LINES[0])

    def test_two_lines_file_separated_read(self):
        obj = self.get_object(TWO_LINES_NAME)
        with obj as line_iter:
            self.assertEqual(next(line_iter), LINES[0])
        self.assertEqual(obj.get_position(), ONE_LINE_POSITION)
        with obj as line_iter:
            self.assertEqual(next(line_iter), LINES[1])
        self.assertEqual(obj.get_position(), TWO_LINES_POSITION)

    def test_file_witout_eol_before_eof(self):
        obj = self.get_object(THREE_LINES_NAME)
        with obj as line_iter:
            self.assertEqual(tuple(line_iter), LINES[:3])
        self.assertEqual(obj.get_position(), THREE_LINES_POSITION)

    def test_position_in_file_witout_eol_before_eof(self):
        obj = self.get_object(THREE_LINES_NAME)
        with obj(*THREE_LINES_POSITION) as line_iter:
            self.assertEqual(obj.get_position(), THREE_LINES_POSITION)
            with self.assertRaises(StopIteration):
                next(line_iter)
        self.assertEqual(obj.get_position(), THREE_LINES_POSITION)

    def test_get_eof_position(self):
        obj = self.get_object(NAME)
        self.assertEqual(obj.get_eof_position(), ctl.DEFAULT_POSITION)
        obj = self.get_object(ONE_LINE_NAME)
        self.assertEqual(obj.get_eof_position(), ONE_LINE_POSITION)
        obj = self.get_object(TWO_LINES_NAME)
        self.assertEqual(obj.get_eof_position(), TWO_LINES_POSITION)
        obj = self.get_object(THREE_LINES_NAME)
        self.assertEqual(obj.get_eof_position(), THREE_LINES_POSITION)

    def test_get_eof_position_on_long_lines(self):
        obj = self.get_object(LONG_LINE_NAME)
        self.assertEqual(obj.get_eof_position(), (0, LONG_LINE))
        obj = self.get_object(TWO_LONG_LINES_NAME)
        self.assertEqual(obj.get_eof_position(), (len(LONG_LINE), LONG_LINE[1:]))


if __name__ == '__main__':
    unittest.main()
