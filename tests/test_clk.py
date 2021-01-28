# -*- encoding: utf-8 -*-
import concurrent.futures
import io
import textwrap
import unittest

from clkhash import clk, schema, randomnames, validate_data
from clkhash.serialization import serialize_bitarray


class TestChunks(unittest.TestCase):

    def test_simple_chunk(self):
        l = list(range(100))
        res = list(clk.chunks(l, 5))
        self.assertEqual(len(res), 20)
        self.assertEqual(len(res[0]), 5)

    def test_uneven_chunk(self):
        l = list(range(17))
        res = list(clk.chunks(l, 10))
        self.assertEqual([0,1,2,3,4,5,6,7,8,9], res[0])
        self.assertEqual([10, 11, 12, 13, 14, 15, 16], res[1])


class TestComplexSchemaChanges(unittest.TestCase):
    CSV_INPUT = textwrap.dedent("""\
        name,id,dob,gender,children
        KÉVIN,kev007,1963-12-13,M,1
        "JOHN HOWARD, ESQ.",stv534,1992-02-29,M,16
        JULIA,alp423,0123-01-12,F,0
        """)

    SCHEMA_DICT = dict(
        version=1,
        clkConfig=dict(
            l=1024,
            k=30,
            kdf=dict(
                type='HKDF',
                hash='SHA256',
                salt='SCbL2zHNnmsckfzchsNkZY9XoHk96P/G5nUBrM7ybymlEFsMV6PAeDZCNp3rfNUPCtLDMOGQHG4pCQpfhiHCyA==',
                info='c2NoZW1hX2V4YW1wbGU=',
                keySize=64),
            hash=dict(
                type='doubleHash')),
        features=[
            dict(
                identifier='name',
                format=dict(
                    type='string',
                    encoding='utf-8',
                    case='upper'),
                hashing=dict(
                    ngram=2,
                    weight=2)),
            dict(
                identifier='id',
                format=dict(
                    type='string',
                    encoding='ascii',
                    pattern=r'[a-z][a-z][a-z]\d\d\d'),
                hashing=dict(
                    ngram=1,
                    positional=True)),
            dict(
                identifier='dob',
                format=dict(
                    type='date',
                    format='%Y-%m-%d',
                    description='When were ya born?'),
                hashing=dict(
                    ngram=2,
                    positional=True,
                    weight=.5)),
            dict(
                identifier='gender',
                format=dict(
                    type='enum',
                    values=['M', 'F']),
                hashing=dict(
                    ngram=1,
                    positional=False)),
            dict(
                identifier='children',
                format=dict(
                    type='integer',
                    maximum=20),
                hashing=dict(
                    ngram=1,
                    positional=True))])
    SECRET = 'chicken'

    def test_expected_number_of_encodings_returned(self):
        loaded_schema = schema.from_json_dict(self.SCHEMA_DICT)

        results = clk.generate_clk_from_csv(
            io.StringIO(self.CSV_INPUT),
            self.SECRET,
            loaded_schema,
            validate=True,
            header=True,
            progress_bar=False)

        assert len(results) == 3

    def test_generate_encodings_setting_max_workers(self):
        loaded_schema = schema.from_json_dict(self.SCHEMA_DICT)

        results = clk.generate_clk_from_csv(
            io.StringIO(self.CSV_INPUT),
            self.SECRET,
            loaded_schema,
            validate=True,
            header=True,
            progress_bar=False,
            max_workers=4)

        assert len(results) == 3

    def test_generate_encodings_with_thread_executor(self):
        loaded_schema = schema.from_json_dict(self.SCHEMA_DICT)

        results = clk.generate_clk_from_csv(
            io.StringIO(self.CSV_INPUT),
            self.SECRET,
            loaded_schema,
            validate=True,
            header=True,
            progress_bar=False,
            max_workers=1)

        assert len(results) == 3

    def test_encoding_regression(self):
        loaded_schema = schema.from_json_dict(self.SCHEMA_DICT)

        results = clk.generate_clk_from_csv(
            io.StringIO(self.CSV_INPUT),
            self.SECRET,
            loaded_schema,
            validate=True,
            header=True,
            progress_bar=False)

        assert serialize_bitarray(results[0]) == 'SU9+/O/Jzzi0sfzH8K2l3+qfhn8Ky3jVI21DVdH9j2fXE++JH8GcQGSeYxDZFxALCAT8CHwYJyQcRT3MhUQOFWcOf5fWdr6ofh6DYy8iv////weyunbMahfV9RMWkRwQmBL3fjreUVOCS9D9kAbQC2XgULidKCTHd9ZpbPJ91eE='
        assert serialize_bitarray(results[1]) == 'Pfl1/d7/31/+9u9x9zv//76/83//0v1Xt/dX/3X/e79XP7vd+Xfkf//2/9Xb/7Fd73e9f/n0f/c7Vb99B/X29d8997Pz/vJ87X/X/vcX9vt1d+/+5bP1fvfevnfX8d/f/j0XPL7f999kc/28/3d4c7t/9b/+Pf411/f2+3z1d/s='


class TestHeaderChecking(unittest.TestCase):
    def setUp(self):
        self.schema = randomnames.NameList.SCHEMA
        self.csv_correct_header = (
            'INDEX,NAME freetext,DOB YYYY/MM/DD,GENDER M or F\n'
            '0,Jane Austen,1775/12/16,F\n'
            '1,Bob Hawke,1929/12/09,M\n'
            '2,Tivadar Kanizsa,1933/04/04,M')
        self.csv_incorrect_header_name = (
            'INDEX,THIS IS INCORRECT,DOB YYYY/MM/DD,GENDER M or F\n'
            '0,Jane Austen,1775/12/16,F\n'
            '1,Bob Hawke,1929/12/09,M\n'
            '2,Tivadar Kanizsa,1933/04/04,M')
        self.csv_incorrect_count = (
            'INDEX,THIS IS INCORRECT,DOB YYYY/MM/DD\n'
            '0,Jane Austen,1775/12/16,F\n'
            '1,Bob Hawke,1929/12/09,M\n'
            '2,Tivadar Kanizsa,1933/04/04,M')
        self.csv_no_header = (
            '0,Jane Austen,1775/12/16,F\n'
            '1,Bob Hawke,1929/12/09,M\n'
            '2,Tivadar Kanizsa,1933/04/04,M')

    def test_header(self):
        out = clk.generate_clk_from_csv(
            io.StringIO(self.csv_correct_header),
            'open sesame',
            self.schema,
            header=True,
            progress_bar=False)
        self.assertEqual(len(out), 3)

        with self.assertRaises(validate_data.FormatError):
            clk.generate_clk_from_csv(
                io.StringIO(self.csv_incorrect_header_name),
                'open sesame',
                self.schema,
                header=True,
                progress_bar=False)

        with self.assertRaises(validate_data.FormatError):
            clk.generate_clk_from_csv(
                io.StringIO(self.csv_incorrect_count),
                'open sesame',
                self.schema,
                header=True,
                progress_bar=False)

        with self.assertRaises(validate_data.FormatError):
            clk.generate_clk_from_csv(
                io.StringIO(self.csv_no_header),
                'open sesame',
                self.schema,
                header=True,
                progress_bar=False)

    def test_ignore_header(self):
        out = clk.generate_clk_from_csv(
            io.StringIO(self.csv_correct_header),
            'open sesame',
            self.schema,
            header='ignore',
            progress_bar=False)
        self.assertEqual(len(out), 3)

        out = clk.generate_clk_from_csv(
            io.StringIO(self.csv_incorrect_header_name),
            'open sesame',
            self.schema,
            header='ignore',
            progress_bar=False)
        self.assertEqual(len(out), 3)

        out = clk.generate_clk_from_csv(
            io.StringIO(self.csv_incorrect_count),
            'open sesame',
            self.schema,
            header='ignore',
            progress_bar=False)
        self.assertEqual(len(out), 3)

        out = clk.generate_clk_from_csv(
            io.StringIO(self.csv_no_header),
            'open sesame',
            self.schema,
            header='ignore',
            progress_bar=False)
        self.assertEqual(len(out), 2)

    def test_no_header(self):
        with self.assertRaises(validate_data.EntryError):
            clk.generate_clk_from_csv(
                io.StringIO(self.csv_correct_header),
                'open sesame',
                self.schema,
                header=False,
                progress_bar=False)

        with self.assertRaises(validate_data.EntryError):
            clk.generate_clk_from_csv(
                io.StringIO(self.csv_incorrect_header_name),
                'open sesame',
                self.schema,
                header=False,
                progress_bar=False)

        with self.assertRaises(validate_data.FormatError):
            clk.generate_clk_from_csv(
                io.StringIO(self.csv_incorrect_count),
                'open sesame',
                self.schema,
                header=False,
                progress_bar=False)

        out = clk.generate_clk_from_csv(
            io.StringIO(self.csv_no_header),
            'open sesame',
            self.schema,
            header=False,
            progress_bar=False)
        self.assertEqual(len(out), 3)
