# -*- coding: utf-8 -*-

""" Classes that specify the requirements for each column in a dataset.
    They take care of validation, and produce the settings required to
    perform the hashing.
"""

import abc
import re
import sre_constants
from typing import Any, cast, Dict, Iterable, Pattern, Optional

from future.utils import raise_from, with_metaclass


def compile_full(pattern, flags=0):
    # type: (str, int) -> Pattern
    """ Create compiled regular expression such that it matches the
        entire string. Calling re.match on the output of this function
        is equivalent to calling re.fullmatch on its input.

        This is needed to support Python 2.
        Kudos: https://stackoverflow.com/a/30212799

        :param pattern: The pattern to compile.
        :param flags: Regular expression flags. Refer to Python
            documentation.

        :returns: A compiled regular expression.
    """
    return re.compile('(?:' + pattern + r')\Z', flags=flags)


class InvalidEntryError(Exception):
    """ An entry in the data file does not conform to the schema.
    """
    pass


class InvalidSchemaError(Exception):
    """ The schema is not valid.

        This exception is raised if, for example, a regular expression
        included in the schema is not syntactically correct.
    """
    pass


class HashingProperties(object):
    """ Stores the information needed to to create a hash from each
        entry of a type.

        :ivar encoding: The encoding to use when converting the string
            to bytes. Refer to Python's documentation for possible
            values.
        :ivar ngram: The n in n-gram. Possible values are 0, 1, and 2.
        :ivar positional: Controls whether the n-grams are positional.
        :ivar weight: Controls the weight of the field in the Bloom
            filter.
    """
    __slots__ = ('encoding', 'gram', 'positional', 'weight')

    DEFAULT_ENCODING = 'utf-8'
    DEFAULT_POSITIONAL = False
    DEFAULT_WEIGHT = 1

    def __init__(self, hash_properties):
        # type: (Dict[str, Any]) -> None
        """ Make a HashingProperties object from a dictionary.

            The dictionary must have have an 'ngram' key. It may have
            'positional' and 'weight' keys; if these are missing, then
            they are filled with the default values. The encoding is
            always set to the default value.

            :param hash_properties: The dictionary to use.
        """
        self.encoding = DEFAULT_ENCODING
        self.ngram = cast(str, hash_properties['ngram'])
        self.positional = cast(str, hash_properties.get('positional',
                                                        DEFAULT_POSITIONAL))
        self.weight = cast(float, hash_properties.get('weight',
                                                      DEFAULT_WEIGHT))


class FieldSpec(with_metaclass(abc.ABCMeta, object)):
    """ Abstract base class representing the specification of a column
        in the dataset. Subclasses validate entries, and produce
        `HashingProperties` objects specifying the settings for
        hashing.

        :ivar hashing_properties: The properties for hashing.
    """
    def __init__(self, properties):
        # type: (Dict[str, Any]) -> None
        """ Initialise a FieldSpec object from a dictionary of
            properties.

            This dictionary must contain a `'hashing'` key that meets
            the requirements of `HashingProperties.__init__`.

            Subclasses may override this method to conduct their own
            initialisation. They should call the parent's initialiser
            via `super`.

            :param properties: The properties dictionary to use.
            :raises InvalidSchemaError: When the `properties`
                dictionary contains invalid values. Exacly what that
                means is decided by the subclasses.
        """
        self.hashing_properties = HashingProperties(
            cast(Dict[str, Any], properties['hashing']))

    @abc.abstractmethod
    def validate(self, str_in):
        # type: (str) -> None
        """ Validates an entry in the field.

            Raises `InvalidEntryError` iff the entry is invalid.

            Subclasses must override this method with their own
            validation. They should call the parent's `validate` method
            via `super`.

            :param str_in: String to validate.
            :raises InvalidEntryError: When entry is invalid.
        """
        try:
            str_in.encode(encoding=self.hashing_properties.encoding)
        except UnicodeEncodeError as e:
            msg = ("Expected entry that can be encoded in {}. Read '{}'."
                   .format(str_in))
            raise_from(InvalidEntryError(msg), e)


class StringSpec(FieldSpec):
    """ Represents a field that holds strings.

        One way to specify the format of the entries is to provide a
        regular expression that they must conform to. Another is to
        provide zero or more of: minimum length, maximum length, casing
        (lower, upper, mixed).

        Each string field also specifies an encoding used when turning
        characters into bytes.

        :ivar regex: Compiled regular expression that entries must
            conform to. Present only if the specification is regex-
            -based.
        :ivar case: The casing of the entries. One of `'lower'`,
            `'upper'`, or `'mixed'`. Default is `'mixed'`. Present only
            if the specification is not regex-based.
        :ivar min_length: The minimum length of the string. `None` if
            there is no minimum length. Present only if the
            specification is not regex-based.
        :ivar max_length: The maximum length of the string. `None` if
            there is no maximum length. Present only if the
            specification is not regex-based.
    """
    DEFAULT_CASE = 'mixed'

    def __init__(self, properties):
        # type: (Dict[str, Any]) -> None
        """ Make a StringSpec object from a dictionary containing its
            properties.

            The dictionary must contain an `'encoding'` key associated
            with a Python-conformant encoding. It must also contain a
            `'hashing'` key, whose contents are passed to
            HashingProperties.__init__.

            Possible keys also include `'pattern'`, `'case'`,
            `'minLength'`, and `'maxLength'`.

            :param properties: The properties dictionary.
            :raises InvalidSchemaError: When a regular expression is
                provided but is not a valid pattern.
        """
        super(StringSpec, self).__init__(properties)
        self.hashing_properties.encoding = cast(str, properties['encoding'])

        if 'pattern' in properties:
            pattern = cast(str, properties['pattern'])
            try:
                self.regex = compile_full(pattern)
            except (SyntaxError, sre_constants.error) as e:
                msg = "Invalid regular expression '{}.'".format(pattern)
                raise_from(InvalidSchemaError(msg), e)

        else:
            self.case = cast(str, properties.get('case', DEFAULT_CASE))
            self.min_length = cast(Optional[int], properties.get('minLength'))
            self.max_length = cast(Optional[int], properties.get('maxLength'))

    def validate(self, str_in):
        # type: (str) -> None
        """ Validates an entry in the field.

            Raises `InvalidEntryError` iff the entry is invalid.

            An entry is invalid iff (1) a pattern is part of the
            specification of the field and the string does not match
            it; (2) the string does not match the provided casing,
            minimum length, or maximum length; or (3) the specified
            encoding cannot represent the string.

            :param str_in: String to validate.
            :raises InvalidEntryError: When entry is invalid.
            :raises ValueError: When self.case is not one of the
                permitted values (`'lower'`, `'upper'`, or `'mixed'`).
        """
        super(StringSpec, self).validate(str_in)  # Validate encoding.

        if hasattr(self, 'regex'):
            match = self.regex.match(str_in)
            if match is None:
                raise InvalidEntryError(
                    'Expected entry that conforms to regular expression '
                    "'{}'. Read '{}'.".format(self.regex.pattern, str_in))

        else:
            str_len = len(str_in)
            if self.min_length is not None and str_len < self.min_length:
                raise InvalidEntryError(
                    'Expected string length of at least {}. Read string of '
                    'length {}.'.format(self.minLength, str_len))

            if self.max_length is not None and str_len > self.max_length:
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
                raise ValueError(
                    'Invalid case property {}.'.format(self.case))


class IntegerSpec(FieldSpec):
    """ Represents a field that holds integers.

        Minimum and maximum values may be specified.

        :ivar minimum: The minimum permitted value.
        :ivar maximum: The maximum permitted value.
    """
    def __init__(self, properties):
        # type: (Dict[str, Any]) -> None
        """ Make a IntegerSpec object from a dictionary containing its
            properties.

            The dictionary may contain `'minimum'` and `'maximum'`
            keys. In addition, it must contain a `'hashing'` key, whose
            contents are passed to HashingProperties.__init__.

            :param properties: The properties dictionary.
        """

        # Don't permit negative integers.
        self.minimum = properties.get('minimum', 0)

        self.maximum = properties.get('maximum')

    def validate(self, str_in):
        # type: (str) -> None
        """ Validates an entry in the field.

            Raises `InvalidEntryError` iff the entry is invalid.

            An entry is invalid iff (1) the string does not represent a
            base-10 integer; (2) the integer is not between
            `self.minimum` and `self.maximum`, if those exist; or (3)
            the integer is negative.

            :param str_in: String to validate.
            :raises InvalidEntryError: When entry is invalid.
        """
        super(IntegerSpec, self).validate(str_in)

        try:
            value = int(str_in, base=10)
        except ValueError as e:
            msg = 'Invalid integer. Read {}.'.format(str_in)
            raise_from(InvalidEntryError(msg), e)

        if value < self.minimum:
            msg = ('Expected integer value of at least {}. Read {}.'
                   .format(value))
            raise InvalidEntryError(msg)

        if self.maximum is not None and value > self.minimum:
            msg = ('Expected integer value of at most {}. Read {}.'
                   .format(value))
            raise InvalidEntryError(msg)


class DateSpec(FieldSpec):
    """ Represents a field that holds dates.

        A format for the date may be specified. Currently, the only
        supported format is RFC3339.

        :ivar format: The format of the date.
    """
    RFC3339_REGEX = compile_full(r'\d\d\d\d-\d\d-\d\d')
    RFC3339_FORMAT = '%Y-%m-%d'

    def __init__(self, properties):
        # type: (Dict[str, Any]) -> None
        """ Make a DateSpec object from a dictionary containing its
            properties.

            The dictionary may contain `'format'` key. In addition, it
            must contain a `'hashing'` key, whose contents are passed
            to HashingProperties.__init__.

            :param properties: The properties dictionary.
        """
        self.format = cast(str, properties['format'])

    def validate(self, str_in):
        # type: (str) -> None
        """ Validates an entry in the field.

            Raises `InvalidEntryError` iff the entry is invalid.

            An entry is invalid iff (1) the string does not represent a
            date in the correct format; or (2) the date it represents
            is invalid (such as 30 February).

            :param str_in: String to validate.
            :raises InvalidEntryError: When entry is invalid.
            :raises ValueError: When self.format is unrecognised.
        """
        super(DateSpec, self).validate(str_in)

        if self.format == 'rfc3339':
            if DateValidator.RFC3339_REGEX.match(str_in) is None:
                msg = ('Date expected to conform to RFC3339. Read {}.'
                       .format(str_in))
                raise InvalidEntryError(msg)
            try:
                datetime.strptime(str_in, DateValidator.RFC3339_FORMAT)
            except ValueError as e:
                msg = 'Invalid date. Read {}.'.format(str_in)
                raise_from(InvalidEntryError(msg), e)

        else:
            msg = 'Unrecognised date format: {}.'.format(self.format)
            raise ValueError(msg)


class EnumSpec(FieldSpec):
    """ Represents a field that holds an enum.

        The finite collection of permitted values must be specified.

        :ivar format: The set of permitted values.
    """
    def __init__(self, properties):
        # type: (Dict[str, Any]) -> None
        """ Make a EnumSpec object from a dictionary containing its
            properties.

            The dictionary must contain `'enum'` key specifying the
            permitted values. In addition, it must contain a
            `'hashing'` key, whose contents are passed to
            HashingProperties.__init__.

            :param properties: The properties dictionary.
        """
        self.values = set(cast[Iterable, properties['enum']])

    def validate(self, str_in):
        # type: (str) -> None
        """ Validates an entry in the field.

            Raises `InvalidEntryError` iff the entry is invalid.

            An entry is invalid iff it is not one of the permitted
            values.

            :param str_in: String to validate.
            :raises InvalidEntryError: When entry is invalid.
        """
        super(EnumSpec, self).validate(str_in)

        if str_in not in self.values:
            msg = 'Expected enum value is one of {}. Read {}.'.format(str_in)
            raise InvalidEntryError(msg)
