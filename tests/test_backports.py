# -*- encoding: utf-8 -*-

from __future__ import unicode_literals

from base64 import b64decode
from datetime import datetime
import io
import itertools
import unittest

from clkhash.backports import (int_from_bytes, re_compile_full,
                               unicode_reader, strftime)


class TestIntBackports(unittest.TestCase):
    def test_big_endian(self):
        self.assertEqual(
            34,
            int_from_bytes(b64decode('Ig=='.encode('ascii')), 'big'),
            msg="Int from bytes doesn't match expected value.")

        self.assertEqual(
            45673,
            int_from_bytes(
                b64decode('AAAAAAAAAACyaQ=='.encode('ascii')),
                'big'),
            msg="Int from bytes doesn't match expected value.")

        self.assertEqual(
            56789876545678987654678987654567898765456789765456787654,
            int_from_bytes(
                b64decode('AlDp+lkU/TxpNjohctiKo3IFkbpFKfjG'.encode('ascii')),
                'big'),
            msg="Int from bytes doesn't match expected value.")

    def test_little_endian(self):
        self.assertEqual(
            34,
            int_from_bytes(b64decode('Ig=='.encode('ascii')), 'little'),
            msg="Int from bytes doesn't match expected value.")

        self.assertEqual(
            45673,
            int_from_bytes(
                b64decode('abIAAAAAAAAAAA=='.encode('ascii')),
                'little'),
            msg="Int from bytes doesn't match expected value.")

        self.assertEqual(
            56789876545678987654678987654567898765456789765456787654,
            int_from_bytes(
                b64decode('xvgpRbqRBXKjithyITo2aTz9FFn66VAC'.encode('ascii')),
                'little'),
            msg="Int from bytes doesn't match expected value.")

    def test_invalid_arg(self):
        with self.assertRaises(
                ValueError,
                msg='Expected raise ValueError on invalid endianness.'):
            int_from_bytes(
                b64decode('abIAAAAAAAAAAA=='.encode('ascii')),
                'lobster')


class TestCompileFull(unittest.TestCase):
    def test_compile_full(self):
        regex = re_compile_full('.?foo(d|bar)')

        # These should match
        self.assertIsNotNone(regex.match('food'))
        self.assertIsNotNone(regex.match('foobar'))
        self.assertIsNotNone(regex.match('0food'))
        self.assertIsNotNone(regex.match('!foobar'))

        # These shouldn't
        self.assertIsNone(regex.match('foodbar'))
        self.assertIsNone(regex.match('foobar0'))
        self.assertIsNone(regex.match('..foobar'))
        self.assertIsNone(regex.match('..foobarz'))


class TestUnicodeReader(unittest.TestCase):
    def test_unicode_reader(self):
        data = [['first', 'last'],
                ['James', 'Morgan'],
                ['Françoise', 'Grossetête'],
                ['القاهرة', 'مِصر‎']]
        
        csv_str = '\n'.join(','.join(row) for row in data)
        csv_str += '\n'  # Trailing newlines are nice.
        f = io.StringIO(csv_str)

        reader = unicode_reader(f)
        read_data = list(reader)
        self.assertEqual(read_data, data)


class TestStrftime(unittest.TestCase):
    def test_recent_years(self):
        self.assertEqual(
            strftime(datetime(1995, 12, 23), '%Y/%m/%d'),
            '1995/12/23')
        self.assertEqual(
            strftime(datetime(2004, 5, 1), '%d-%m-%Y'),
            '01-05-2004')

    def test_nonnative_years(self):
        self.assertEqual(
            strftime(datetime(1884, 2, 29), '%Y/%m/%d'),
            '1884/02/29')
        self.assertEqual(
            strftime(datetime(1000, 1, 2), '%d-%m-%Y'),
            '02-01-1000')

    def test_short_years(self):
        self.assertEqual(
            strftime(datetime(942, 2, 12), '%Y/%m/%d'),
            '0942/02/12')
        self.assertEqual(
            strftime(datetime(43, 1, 2), '%d-%m-%Y'),
            '02-01-0043')
        self.assertEqual(
            strftime(datetime(1, 3, 16), '%d-%m-%Y'),
            '16-03-0001')
