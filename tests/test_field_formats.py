# -*- coding: utf-8 -*-

import math
import unittest

from clkhash import field_formats, comparators


class TestFieldFormats(unittest.TestCase):
    bigram_tokenizer = comparators.NgramComparison(2)

    def check_ngram_comparator(self, comparator, n, positional):
        self.assertIsInstance(comparator, comparators.NgramComparison)
        self.assertEquals(comparator.n, n)
        self.assertEquals(comparator.positional, positional)

    def test_string_regex(self):
        regex_spec = dict(
            identifier='regex',
            format=dict(
                type='string',
                encoding='ascii',
                pattern=r'[5-9',  # This is syntactically incorrect.
                description='foo'),
            hashing=dict(comparison=dict(type='ngram', n=1), strategy=dict(bitsPerToken=20)))

        # Make sure we don't accept bad regular expressions.
        with self.assertRaises(field_formats.InvalidSchemaError):
            field_formats.spec_from_json_dict(regex_spec)

        # Ok, let's fix it. This should not raise.
        regex_spec['format']['pattern'] = r'dog(.dog)*'
        spec = field_formats.spec_from_json_dict(regex_spec)

        # Ensure we accept these.
        spec.validate('dog')
        spec.validate('dogodog')

        # These don't match the pattern.
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('dogs')
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('hot dog')
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('hot dogs')

        # This should raise since 'ø' can't be represented by our
        # encoding (ASCII).
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate(u'dogødog')

        # Check random metadata.
        self.assertEqual(spec.identifier, 'regex')
        self.assertEqual(spec.description, 'foo')

        # Finally, check the hashing specs.
        self.check_ngram_comparator(spec.hashing_properties.comparator, 1, False)
        self.assertIsInstance(spec.hashing_properties.strategy, field_formats.BitsPerTokenStrategy)
        self.assertEqual(spec.hashing_properties.strategy.bits_per_token, 20)

        # check with missing values
        regex_spec['hashing']['missingValue'] = dict(sentinel='null')
        spec = field_formats.spec_from_json_dict(regex_spec)
        # validating the sentinel should work
        spec.validate('null')
        self.assertTrue(spec.is_missing_value('null'))
        self.assertFalse(spec.is_missing_value('dog'))
        self.assertEqual('null', spec.hashing_properties.replace_missing_value('null'))
        self.assertEqual('dog', spec.hashing_properties.replace_missing_value('dog'))
        # now with replaceWith value
        regex_spec['hashing']['missingValue']['replaceWith'] = 'cat'
        spec = field_formats.spec_from_json_dict(regex_spec)
        self.assertEqual('cat', spec.hashing_properties.replace_missing_value('null'))
        # check invalid format specs
        hashing_properties = field_formats.FieldHashingProperties(
            comparator=self.bigram_tokenizer, strategy=field_formats.BitsPerTokenStrategy(20))
        with self.assertRaises(ValueError):
            spec = field_formats.StringSpec(
                identifier='regex',
                hashing_properties=hashing_properties,
                case='casey',
                regex=r'dog(.dog)*')
        with self.assertRaises(field_formats.InvalidEntryError):
            spec = field_formats.StringSpec(
                identifier='regex',
                hashing_properties=hashing_properties,
                regex=r'[5-9')

    def test_string_nonregex_from_json_dict(self):
        spec_dict = dict(
            identifier='noRegex',
            format=dict(
                # note 'minLength' and 'maxLength' are missing.
                type='string',
                encoding='utf-8',
                description='bar'),
            hashing=dict(
                comparison=dict(n=1, type='ngram'),
                positional=True,
                strategy=dict(bitsPerToken=20)))

        spec = field_formats.spec_from_json_dict(spec_dict)

        # The min and max lengths should be None.
        self.assertIsNone(spec.min_length)
        self.assertIsNone(spec.max_length)

        # There are no length limits so these should be fine.
        spec.validate('')
        spec.validate('doggo' * 10000)

        # Ok, let's put a 'minLength' and 'maxLength' in.
        spec_dict['format']['minLength'] = 5
        spec_dict['format']['maxLength'] = 8
        spec = field_formats.spec_from_json_dict(spec_dict)

        # These are not fine anymore.
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('')
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('dogs')
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('doggodogs')
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('doggo' * 10000)

        # These are ok though.
        spec.validate('doggo')
        spec.validate('doggos')
        spec.validate('doggies!')

        # This should be fine since we specified utf-8 as the encoding.
        spec.validate(u'doggøs')

        # Check random metadata.
        self.assertEqual(spec.identifier, 'noRegex')
        self.assertEqual(spec.description, 'bar')

        # Check the hashing specs.
        self.check_ngram_comparator(spec.hashing_properties.comparator, 1, False)
        self.assertIsInstance(spec.hashing_properties.strategy, field_formats.BitsPerTokenStrategy)
        self.assertEqual(spec.hashing_properties.strategy.bits_per_token, 20)

        # check with missing values
        spec_dict['hashing']['missingValue'] = dict(sentinel='N/A')
        spec = field_formats.spec_from_json_dict(spec_dict)
        # validating the sentinel should work
        spec.validate('N/A')

    def test_string_nonregex_init(self):
        hashing_properties = field_formats.FieldHashingProperties(
            comparator=self.bigram_tokenizer, strategy=field_formats.BitsPerTokenStrategy(20))
        spec = field_formats.StringSpec(
            identifier='first name',
            hashing_properties=hashing_properties,
            case='mixed',
            min_length=5)

        # The min should be set, and max length should be None.
        self.assertEqual(spec.min_length, 5)
        self.assertIsNone(spec.max_length)

        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('hi')
        spec.validate('hello this is fine')
        spec.validate('Hello This is FINE!')
        spec.case = 'lower'
        spec.validate('hello you')
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('Hello You')
        spec.case = 'upper'
        spec.validate('HELLO SHOUTY')
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('Hello You')
        spec.case = 'casey'
        with self.assertRaises(ValueError):
            spec.validate('boomboom')

        # Check random metadata.
        self.assertEqual(spec.identifier, 'first name')
        self.assertIsNone(spec.description)

        # Check the hashing specs.
        self.assertTrue(hasattr(spec, 'hashing_properties'))
        # check invalid field specs
        with self.assertRaises(ValueError):
            field_formats.StringSpec(
                identifier='first name',
                hashing_properties=hashing_properties,
                case='mixed',
                min_length=-5)
        with self.assertRaises(ValueError):
            field_formats.StringSpec(
                identifier='first name',
                hashing_properties=hashing_properties,
                case='mixed',
                max_length=-1)
        with self.assertRaises(ValueError):
            field_formats.StringSpec(
                identifier='first name',
                hashing_properties=hashing_properties,
                case='caseychasey')

    def test_string_default_encoding_nonregex(self):
        spec_dict = dict(
            identifier='stringWithoutEncoding',
            format=dict(type='string'),
            hashing=dict(
                comparison=dict(type='ngram', n=1, positional=True),
                strategy=dict(bitsPerToken=20)))

        spec = field_formats.spec_from_json_dict(spec_dict)

        # These are fine since the default encoding is utf-8.
        spec.validate('dogs')
        spec.validate('cats')
        spec.validate(u'fërrets')  # Test Unicode.

        self.assertEqual(spec.hashing_properties.encoding, 'utf-8')

    def test_string_default_encoding_regex(self):
        spec_dict = dict(
            identifier='stringWithoutEncoding',
            format=dict(
                type='string',
                pattern='f.+'),
            hashing=dict(
                comparison=dict(type='ngram', n=1, positional=True),
                strategy=dict(bitsPerToken=20)))

        spec = field_formats.spec_from_json_dict(spec_dict)

        # These are fine since the default encoding is utf-8.
        spec.validate('fur')
        spec.validate(u'fërrets')  # Test Unicode.

        # These don't match the pattern.
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('cats')
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('dogs')

        self.assertEqual(spec.hashing_properties.encoding, 'utf-8')

    def test_integer(self):
        json_spec = {
            'identifier': 'Z',
            'format': {
                # Missing 'minimum' and 'maximum'.
                'type': 'integer',
                'description': 'buzz'
            },
            'hashing': {
                'comparison': {'type': 'ngram', 'n': 1, 'positional': True},
                'strategy': {'bitsPerToken': 20}
            }
        }

        spec = field_formats.spec_from_json_dict(json_spec)

        # `minimum` and `maximum` should be None.
        self.assertIsNone(spec.minimum)
        self.assertIsNone(spec.maximum)

        # There are no bounds so these should be fine.
        spec.validate('-31')
        spec.validate('0')
        spec.validate('1')
        spec.validate('10')
        spec.validate(str(10 ** 321))

        # We don't like floats.
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate(str(math.pi))
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate(str(-math.pi))
        # or strings
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('boom')
        with self.assertRaises(ValueError):
            spec.format_value('boom')

        # There are several valid integer strings for one integer
        for int_str in ['  10', '10  ', '+10', ' +10 ']:
            spec.validate(int_str)
            self.assertEqual('10', spec.format_value(int_str))

        # Ok, let's put a 'minimum' and 'maximum' in.

        json_spec['format']['minimum'] = 8
        json_spec['format']['maximum'] = 12
        spec = field_formats.spec_from_json_dict(json_spec)

        # These are too small, thus invalid.
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('-1')
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate(str(-math.pi))
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('0')
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('1')
        # too big, I assume
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate(str(10 ** 321))

        # These are still good.
        spec.validate('8')
        spec.validate('9')
        spec.validate('12')

        # Check random metadata.
        self.assertEqual(spec.identifier, 'Z')
        self.assertEqual(spec.description, 'buzz')

        # Check the hashing specs.
        self.check_ngram_comparator(spec.hashing_properties.comparator, 1, True)
        self.assertIsInstance(spec.hashing_properties.strategy, field_formats.BitsPerTokenStrategy)
        self.assertEqual(spec.hashing_properties.strategy.bits_per_token, 20)

        # check with missing values
        json_spec['hashing']['missingValue'] = dict(sentinel='None', replaceWith='42')
        spec = field_formats.spec_from_json_dict(json_spec)
        # validating the sentinel should work
        spec.validate('None')
        self.assertEqual('42', spec.hashing_properties.replace_missing_value('None'))

    def test_date(self):
        json_spec = {
            'identifier': 'dates',
            'format': {
                'type': 'date', 'format': '%Y-%m-%d',
                'description': 'phoenix dactylifera'},
            'hashing': {'comparison': {'type': 'ngram', 'n': 0}, 'strategy': {'bitsPerToken': 20}}
        }

        spec = field_formats.spec_from_json_dict(json_spec)

        # These are valid dates.
        spec.validate('1946-06-14')
        spec.validate('1977-12-31')
        spec.validate('1981-10-30')
        spec.validate('2006-03-20')

        # These are less valid.
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('0000-03-20')
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('2006-00-20')
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('2006-13-20')
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('2006-03-00')
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('2006-03-52')

        # These formats are incorrect.
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('194-06-14')
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('1946--06-14')
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('194606-14')
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('1946-06--14')
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('1946-0614')
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('2006-3-20d')
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('d2006-3-20')
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('')
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('asdfghjkl')
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('20-03-2006')

        # These are valid dates.
        spec.validate('2017-12-31')
        spec.validate('2017-02-28')
        spec.validate('2017-03-30')
        spec.validate('2016-02-29')
        spec.validate('2000-02-29')

        # These are not.
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('2017-11-31')
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('2017-02-29')
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('2016-02-30')
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('1900-02-29')

        # Check random metadata.
        self.assertEqual(spec.identifier, 'dates')
        self.assertEqual(spec.description, 'phoenix dactylifera')

        # Check the hashing specs.
        self.check_ngram_comparator(spec.hashing_properties.comparator, 0, False)
        self.assertIsInstance(spec.hashing_properties.strategy, field_formats.BitsPerTokenStrategy)
        self.assertEqual(spec.hashing_properties.strategy.bits_per_token, 20)

        # check for graceful fail if format spec is invalid
        spec.format = 'invalid%'
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('2018-01-23')

    def test_date_output_formatting(self):
        regex_spec = dict(
            identifier='dates',
            format=dict(
                type='date',
                format='%Y:%m-%d'),
            hashing=dict(comparison=dict(type="ngram", n=0), strategy=dict(bitsPerToken=20)))
        spec = field_formats.spec_from_json_dict(regex_spec)
        from datetime import date
        from clkhash.field_formats import DateSpec
        d = date.today()
        assert spec.format_value(d.strftime(regex_spec['format']['format'])) == d.strftime(DateSpec.OUTPUT_FORMAT)
        with self.assertRaises(ValueError):
            spec.format_value('yesterday')

    def test_enum(self):
        spec_dict = {
            'identifier': 'testingAllTheEnums',
            'format': {
                'type': 'enum',
                'values': ['dogs', 'cats', u'fërrets'],
                'description': 'fizz'},
            'hashing': {'comparison': {'type': 'ngram', 'n': 2}, 'strategy': {'bitsPerToken': 20}}}

        spec = field_formats.spec_from_json_dict(spec_dict)

        # These are fine.
        spec.validate('dogs')
        spec.validate('cats')
        spec.validate(u'fërrets')  # Test Unicode.

        # These are not.
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('')
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('mice')
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('snakes')
        with self.assertRaises(field_formats.InvalidEntryError):
            spec.validate('dogsdogs')

        # Check random metadata.
        self.assertEqual(spec.identifier, 'testingAllTheEnums')
        self.assertEqual(spec.description, 'fizz')

        # Check the hashing specs.
        self.check_ngram_comparator(spec.hashing_properties.comparator, 2, False)
        self.assertIsInstance(spec.hashing_properties.strategy, field_formats.BitsPerTokenStrategy)
        self.assertEqual(spec.hashing_properties.strategy.bits_per_token, 20)

        # check missing values
        spec_dict['hashing']['missingValue']=dict(sentinel='', replaceWith='omg')
        spec = field_formats.spec_from_json_dict(spec_dict)
        # that's the sentinel for missing values
        spec.validate('')
        # check the missing value related functions in spec
        self.assertTrue(spec.is_missing_value(''))
        self.assertFalse(spec.is_missing_value('no WAY'))
        self.assertEqual(spec.hashing_properties.missing_value.replace_with,
                         spec.hashing_properties.replace_missing_value(''))

    def test_ignored(self):
        spec_dict = {
            'identifier': 'testingIgnored',
            'ignored': True}
        spec = field_formats.spec_from_json_dict(spec_dict)
        self.assertIsInstance(spec, field_formats.Ignore)
        self.assertEqual(spec.identifier, 'testingIgnored')
        spec_dict = {
            'identifier': 'testingIgnored',
            'ignored': False}
        with self.assertRaises(field_formats.InvalidSchemaError):
            field_formats.spec_from_json_dict(spec_dict)
        spec_dict = {
            'identifier': 'ignoredDates',
            'ignored': True,
            'format': {
                'type': 'date', 'format': '%Y-%m-%d'},
            'hashing': {'comparison': {'type': 'ngram', 'n': 0}, 'strategy': {'bitsPerToken': 20}}
        }
        spec = field_formats.spec_from_json_dict(spec_dict)
        self.assertIsInstance(spec, field_formats.Ignore)
        self.assertEqual(spec.identifier, 'ignoredDates')
        spec_dict = {
            'identifier': 'notIgnoredDates',
            'ignored': False,
            'format': {
                'type': 'date', 'format': '%Y-%m-%d'},
            'hashing': {'comparison': {'type': 'ngram', 'n': 0}, 'strategy': {'bitsPerToken': 20}}
        }
        spec = field_formats.spec_from_json_dict(spec_dict)
        self.assertIsNotNone(spec.hashing_properties)
        self.assertIsInstance(spec, field_formats.DateSpec)
        self.assertEqual(spec.identifier, 'notIgnoredDates')
