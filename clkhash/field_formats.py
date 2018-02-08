import abc
import re
import sre_constants

from future.utils import raise_from, with_metaclass


def compile_full(pattern, flags=0):
    # In Python 3, we'd just use re.fullmatch. However, to support
    # Python 2, we have this.
    # Kudos: https://stackoverflow.com/a/30212799
    return re.compile("(?:" + pattern + r")\Z", flags=flags)


class InvalidEntryError(Exception):
    pass


class InvalidSchemaError(Exception):
    pass


class HashingProperties(object):
    DEFAULT_ENCODING = 'utf-8'
    DEFAULT_POSITIONAL = False
    DEFAULT_WEIGHT = 1

    def __init__(self, hash_properties):
        self.encoding = DEFAULT_ENCODING
        self.ngram = hash_properties['ngram']
        self.positional = hash_properties.get('positional', DEFAULT_POSITIONAL)
        self.weight = hash_properties.get('weight', DEFAULT_WEIGHT)


class FieldSpec(with_metaclass(abc.ABCMeta, object)):
    def __init__(self, properties):
        self.hashing_properties = HashingProperties(properties['hashing'])

    @abc.abstractmethod
    def validate(self, str_in):
        try:
            str_in.encode(encoding=self.hashing_properties.encoding)
        except UnicodeEncodeError:
            raise InvalidEntryError(
                "Expected entry that can be encoded in {}. Read '{}'."
                .format(str_in))


class StringSpec(FieldSpec):
    DEFAULT_CASE = 'mixed'

    def __init__(self, properties):
        super(StringSpec, self).__init__(properties)
        self.hashing_properties.encoding = properties['encoding']

        if 'pattern' in properties:
            pattern = properties['pattern']
            try:
                self.pattern = compile_full(pattern)
            except (SyntaxError, sre_constants.error) as e:
                msg = "Invalid regular expression '{}.'".format(pattern)
                raise_from(InvalidSchemaError(msg), e)
        else:
            self.case = properties.get('case', DEFAULT_CASE)
            self.minLength = properties.get('minLength')
            self.maxLength = properties.get('maxLength')

    def validate(self, str_in):
        super(StringSpec, self).validate(str_in)

        if hasattr(self, 'pattern'):
            # TODO: Make this work in Python 2.
            match = self.pattern.fullmatch(str_in)
            if match is None:
                raise InvalidEntryError(
                    'Expected entry that conforms to regular expression '
                    "'{}'. Read '{}'.".format(c.pattern, str_in))
        else:
            str_len = len(str_in)
            if self.minLength is not None and str_len < self.minLength:
                raise InvalidEntryError(
                    'Expected string length of at least {}. Read string of '
                    'length {}.'.format(self.minLength, str_len))

            if self.maxLength is not None and str_len > self.maxLength:
                raise InvalidEntryError(
                    'Expected string length of at most {}. Read string of '
                    'length {}.'.format(self.maxLength, str_len))

            if self.case == 'upper':
                if str_in.upper() != str_in:
                    raise InvalidEntryError(
                        'Expected upper case string. Read {}.'.format(str_in))
            elif self.case == 'lower':
                if str_in.lower() != str_in:
                    raise InvalidEntryError(
                        'Expected lower case string. Read {}.'.format(str_in))
            elif self.case == 'mixed':
                pass
            else:
                raise InvalidSchemaError(
                    'Invalid case property {}.'.format(self.case))


class IntegerSpec(FieldSpec):
    def __init__(self, properties):
        # TODO: Should we permit negative integers?
        # Uncomment below if no.
        self.minimum = properties.get('minimum')  #, 0)
        self.maximum = properties.get('maximum')

    def validate(self, str_in):
        super(IntegerSpec, self).validate(str_in)

        try:
            value = int(str_in, base=10)
        except ValueError as e:
            raise_from(InvalidEntryError('Invalid integer. Read {}.'
                                         .format(str_in)), e)

        if self.minimum is not None and value < self.minimum:
            raise InvalidEntryError('Expected integer value of at least {}.'
                                    'Read {}.'.format(value))

        if self.maximum is not None and value > self.minimum:
            raise InvalidEntryError('Expected integer value of at most {}.'
                                    'Read {}.'.format(value))


class DateSpec(FieldSpec):
    RFC3339_REGEX = compile_full(r'\d\d\d\d-\d\d-\d\d')
    RFC3339_FORMAT = '%Y-%m-%d'

    def __init__(self, properties):
        self.format = properties['format']

    def validate(self, str_in):
        super(DateSpec, self).validate(str_in)

        if self.format == 'rfc3339':
            if DateValidator.RFC3339_REGEX.match(str_in) is None:
                raise InvalidEntryError('Date expected to conform to '
                                        'RFC3339. Read {}.'.format(str_in))
            try:
                datetime.strptime(str_in, DateValidator.RFC3339_FORMAT)
            except ValueError as e:
                raise_from(InvalidEntryError('Invalid date. Read {}.'
                                             .format(str_in)), e)

        else:
            raise ValueError('Unrecognised date format: {}.'
                             .format(self.format))


class EnumSpec(FieldSpec):
    def __init__(self, properties):
        self.values = set(properties['enum'])

    def validate(self, str_in):
        super(EnumSpec, self).validate(str_in)

        if str_in not in self.values:
            raise InvalidEntryError('Expected enum value is one of {}. Read '
                                    '{}.'.format(str_in))
