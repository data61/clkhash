# -*- coding: utf-8 -*-

import math
import unittest

from clkhash import field_formats


class TestFieldFormats(unittest.TestCase):
    def test_string_regex(self):
        regex_spec = dict(
            identifier='regex',
            format=dict(
                type='string',
                encoding='ascii',
                pattern=r'[5-9',  # This is syntactically incorrect.
                description='foo'),
            hashing=dict(
                ngram=1))

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
        self.assertEqual(spec.hashing_properties.ngram, 1)
        self.assertIs(spec.hashing_properties.positional, False)
        self.assertEqual(spec.hashing_properties.weight, 1)

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

    def test_string_nonregex_from_json_dict(self):
        spec_dict = dict(
            identifier='noRegex',
            format=dict(
                # note 'minLength' and 'maxLength' are missing.
                type='string',
                encoding='utf-8',
                description='bar'),
            hashing=dict(
                ngram=1,
                positional=True,
                weight=0))

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
        self.assertEqual(spec.hashing_properties.ngram, 1)
        self.assertIs(spec.hashing_properties.positional, True)
        self.assertEqual(spec.hashing_properties.weight, 0)

        # check with missing values
        spec_dict['hashing']['missingValue'] = dict(sentinel='N/A')
        spec = field_formats.spec_from_json_dict(spec_dict)
        # validating the sentinel should work
        spec.validate('N/A')

    def test_string_nonregex_init(self):
        hashing_properties = field_formats.FieldHashingProperties(
            ngram=2, encoding='utf-8')
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

        # Check random metadata.
        self.assertEqual(spec.identifier, 'first name')
        self.assertIsNone(spec.description)

        # Check the hashing specs.
        self.assertTrue(hasattr(spec, 'hashing_properties'))


    def test_integer(self):
        regex_spec = dict(
            identifier='Z',
            format=dict(
                # Missing 'minimum' and 'maximum'.
                type='integer',
                description='buzz'),
            hashing=dict(
                ngram=1,
                positional=True))

        spec = field_formats.spec_from_json_dict(regex_spec)

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

        # There are several valid integer strings for one integer
        for int_str in ['  10', '10  ', '+10', ' +10 ']:
            spec.validate(int_str)
            self.assertEqual('10', spec.format_value(int_str))

        # Ok, let's put a 'minimum' and 'maximum' in.
        regex_spec['format']['minimum'] = 8
        regex_spec['format']['maximum'] = 12
        spec = field_formats.spec_from_json_dict(regex_spec)

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
        self.assertEqual(spec.hashing_properties.ngram, 1)
        self.assertIs(spec.hashing_properties.positional, True)
        self.assertEqual(spec.hashing_properties.weight, 1)

        # check with missing values
        regex_spec['hashing']['missingValue'] = dict(sentinel='None', replaceWith='42')
        spec = field_formats.spec_from_json_dict(regex_spec)
        # validating the sentinel should work
        spec.validate('None')
        self.assertEqual('42', spec.hashing_properties.replace_missing_value('None'))

    def test_date(self):
        regex_spec = dict(
            identifier='dates',
            format=dict(
                type='date',
                format='%Y-%m-%d',
                description='phoenix dactylifera'),
            hashing=dict(
                ngram=0,
                positional=False,
                weight=1))

        spec = field_formats.spec_from_json_dict(regex_spec)

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
        self.assertEqual(spec.hashing_properties.ngram, 0)
        self.assertIs(spec.hashing_properties.positional, False)
        self.assertEqual(spec.hashing_properties.weight, 1)

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
            hashing=dict(ngram=0))

        spec = field_formats.spec_from_json_dict(regex_spec)
        from datetime import date
        from clkhash.field_formats import DateSpec
        d = date.today()
        assert spec.format_value(d.strftime(regex_spec['format']['format'])) == d.strftime(DateSpec.OUTPUT_FORMAT)

    def test_enum(self):
        spec_dict = dict(
            identifier='testingAllTheEnums',
            format=dict(
                type='enum',
                values=['dogs', 'cats', u'fërrets'],
                description='fizz'),
            hashing=dict(
                ngram=2,
                positional=False,
                weight=2.57))

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
        self.assertEqual(spec.hashing_properties.ngram, 2)
        self.assertIs(spec.hashing_properties.positional, False)
        self.assertEqual(spec.hashing_properties.weight, 2.57)

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
