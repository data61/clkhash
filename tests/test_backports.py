# -*- encoding: utf-8 -*-

from __future__ import unicode_literals

from base64 import b64decode
import io
import itertools
import unittest

from clkhash.backports import int_from_bytes, re_compile_full, unicode_reader


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
