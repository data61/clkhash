# -*- coding: utf-8 -*-

""" Classes that specify the requirements for each column in a dataset.
    They take care of validation, and produce the settings required to
    perform the hashing.
"""

from __future__ import unicode_literals

import abc
from datetime import datetime
import sre_constants
from typing import Any, cast, Dict, Optional, Text

from future.builtins import super
from future.utils import raise_from
from six import add_metaclass

from clkhash.backports import re_compile_full


class InvalidEntryError(ValueError):
    """ An entry in the data file does not conform to the schema.
    """
    pass


class InvalidSchemaError(ValueError):
    """ The schema is not valid.

        This exception is raised if, for example, a regular expression
        included in the schema is not syntactically correct.
    """
    # TODO: Consider getting rid of this and just using ValueError
    # instead.
    pass


class FieldHashingProperties(object):
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
    __slots__ = ('encoding', 'ngram', 'positional', 'weight')

    DEFAULT_ENCODING = 'utf-8'
    DEFAULT_POSITIONAL = False
    DEFAULT_WEIGHT = 1

    def __init__(self, **kwargs):
        # type: (...) -> None
        """ Make a FieldHashingProperties object from keyword
            arguments.

            :param encoding: (optional) Value of `self.encoding`.
            :param ngram: (optional) Value of `self.ngram`.
            :param positional: (optional) Value of `self.positional`.
            :param weight: (optional) Value of `self.weight`.
        """
        if 'encoding' in kwargs:
            self.encoding = kwargs['encoding']
        if 'ngram' in kwargs:
            self.ngram = kwargs['ngram']
        if 'positional' in kwargs:
            self.positional = kwargs['positional']
        if 'weight' in kwargs:
            self.weight = kwargs['weight']

    @classmethod
    def from_json_dict(cls, json_dict):
        # type: (Dict[str, Any]) -> FieldHashingProperties
        """ Make a HashingProperties object from a dictionary.

            The dictionary must have have an 'ngram' key. It may have
            'positional' and 'weight' keys; if these are missing, then
            they are filled with the default values. The encoding is
            always set to the default value.

            :param hash_properties: The dictionary to use.
        """
        result = cls()

        result.encoding = FieldHashingProperties.DEFAULT_ENCODING
        result.ngram = json_dict['ngram']
        result.positional = json_dict.get(
            'positional',
            FieldHashingProperties.DEFAULT_POSITIONAL)
        result.weight = json_dict.get(
            'weight',
            FieldHashingProperties.DEFAULT_WEIGHT)

        return result


@add_metaclass(abc.ABCMeta)
class FieldSpec(object):
    """ Abstract base class representing the specification of a column
        in the dataset. Subclasses validate entries, and modify the
        hashing_properties ivar to customise hashing procedures.

        :ivar identifier: The name of the field.
        :ivar description: Description of the field format.
        :ivar hashing_properties: The properties for hashing.
    """
    def __init__(self, **kwargs):
        # type: (...) -> None
        """ Make a HashingProperties object from keyword arguments.

            :param identifier: (optional) Value of `self.identifier`.
            :param description: (optional) Value of `self.description`.
            :param hashing_properties: (optional) Value of
                `self.hashing_properties`.
        """
        if 'identifier' in kwargs:
            self.identifier = kwargs['identifier']
        if 'description' in kwargs:
            self.description = kwargs['description']
        if 'hashing_properties' in kwargs:
            self.hashing_properties = kwargs['hashing_properties']

    @classmethod
    def from_json_dict(cls, field_dict):
        # type: (Dict[str, Any]) -> FieldSpec
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
        result = cls()

        result.identifier = field_dict['identifier']
        result.description = field_dict['format'].get('description')
        result.hashing_properties = FieldHashingProperties.from_json_dict(
            field_dict['hashing'])

        return result

    @abc.abstractmethod
    def validate(self, str_in):
        # type: (Text) -> None
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
                   .format(self.hashing_properties.encoding, str_in))
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

    def __init__(self, **kwargs):
        # type(...) -> None
        """ Make a HashingProperties object from keyword arguments.

            :param regex: (optional) Value of `self.regex`.
            :param case: (optional) Value of `self.case`.
            :param min_length: (optional) Value of `self.min_length`.
            :param max_length: (optional) Value of `self.max_length`.
        """
        super().__init__(**kwargs)

        if 'regex' in kwargs:
            self.regex = kwargs['regex']
        if 'case' in kwargs:
            self.case = kwargs['case']
        if 'min_length' in kwargs:
            self.min_length = kwargs['min_length']
        if 'max_length' in kwargs:
            self.max_length = kwargs['max_length']

    @classmethod
    def from_json_dict(self, json_dict):
        # type: (Dict[str, Any]) -> StringSpec
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
        result = cast(StringSpec,  # Go away, Mypy.
                      super().from_json_dict(json_dict))

        format_ = json_dict['format']
        result.hashing_properties.encoding = format_['encoding']

        if 'pattern' in format_:
            pattern = format_['pattern']
            try:
                result.regex = re_compile_full(pattern)
            except (SyntaxError, sre_constants.error) as e:
                msg = "Invalid regular expression '{}.'".format(pattern)
                raise_from(InvalidSchemaError(msg), e)

        else:
            result.case = format_.get('case', StringSpec.DEFAULT_CASE)
            result.min_length = format_.get('minLength')
            result.max_length = format_.get('maxLength')

        return result

    def validate(self, str_in):
        # type: (Text) -> None
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
        super().validate(str_in)  # Validate encoding.

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
                    'length {}.'.format(self.min_length, str_len))

            if self.max_length is not None and str_len > self.max_length:
                raise InvalidEntryError(
                    'Expected string length of at most {}. Read string of '
                    'length {}.'.format(self.max_length, str_len))

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
        :ivar maximum: The maximum permitted value or None.
    """
    def __init__(self, **kwargs):
        # type: (...) -> None
        """ Make a HashingProperties object from keyword arguments.

            :param minimum: (optional) Value of `self.minimum`.
            :param maximum: (optional) Value of `self.maximum`.
        """
        super().__init__(**kwargs)

        if 'minimum' in kwargs:
            self.minimum = kwargs['minimum']
        if 'maximum' in kwargs:
            self.maximum = kwargs['maximum']

    @classmethod
    def from_json_dict(cls, json_dict):
        # type: (Dict[str, Any]) -> IntegerSpec
        """ Make a IntegerSpec object from a dictionary containing its
            properties.

            The dictionary may contain `'minimum'` and `'maximum'`
            keys. In addition, it must contain a `'hashing'` key, whose
            contents are passed to HashingProperties.__init__.

            :param properties: The properties dictionary.
        """
        result = cast(IntegerSpec,  # For Mypy.
                      super().from_json_dict(json_dict))

        format_ = json_dict['format']

        result.minimum = format_.get('minimum', 0)  # No integers < 0.
        result.maximum = format_.get('maximum')

        return result

    def validate(self, str_in):
        # type: (Text) -> None
        """ Validates an entry in the field.

            Raises `InvalidEntryError` iff the entry is invalid.

            An entry is invalid iff (1) the string does not represent a
            base-10 integer; (2) the integer is not between
            `self.minimum` and `self.maximum`, if those exist; or (3)
            the integer is negative.

            :param str_in: String to validate.
            :raises InvalidEntryError: When entry is invalid.
        """
        super().validate(str_in)

        try:
            value = int(str_in, base=10)
        except ValueError as e:
            msg = 'Invalid integer. Read {}.'.format(str_in)
            raise_from(InvalidEntryError(msg), e)

        if value < self.minimum:
            msg = ('Expected integer value of at least {}. Read {}.'
                   .format(self.minimum, value))
            raise InvalidEntryError(msg)

        if self.maximum is not None and value > self.maximum:
            msg = ('Expected integer value of at most {}. Read {}.'
                   .format(self.maximum, value))
            raise InvalidEntryError(msg)


class DateSpec(FieldSpec):
    """ Represents a field that holds dates.

        A format for the date may be specified. Currently, the only
        supported format is RFC3339.

        :ivar format: The format of the date.
    """
    RFC3339_REGEX = re_compile_full(r'\d\d\d\d-\d\d-\d\d')
    RFC3339_FORMAT = '%Y-%m-%d'

    def __init__(self, **kwargs):
        # type: (...) -> None
        """ Make a HashingProperties object from keyword arguments.

            :param format: (optional) Value of `self.format`.
        """
        super().__init__(**kwargs)

        if 'format' in kwargs:
            self.format = kwargs['format']

    @classmethod
    def from_json_dict(cls, json_dict):
        # type: (Dict[str, Any]) -> DateSpec
        """ Make a DateSpec object from a dictionary containing its
            properties.

            The dictionary may contain `'format'` key. In addition, it
            must contain a `'hashing'` key, whose contents are passed
            to HashingProperties.__init__.

            :param properties: The properties dictionary.
        """
        result = cast(DateSpec,  # For Mypy.
                      super().from_json_dict(json_dict))

        format_ = json_dict['format']
        result.format = format_['format']

        return result

    def validate(self, str_in):
        # type: (Text) -> None
        """ Validates an entry in the field.

            Raises `InvalidEntryError` iff the entry is invalid.

            An entry is invalid iff (1) the string does not represent a
            date in the correct format; or (2) the date it represents
            is invalid (such as 30 February).

            :param str_in: String to validate.
            :raises InvalidEntryError: When entry is invalid.
            :raises ValueError: When self.format is unrecognised.
        """
        super().validate(str_in)

        if self.format == 'rfc3339':
            if DateSpec.RFC3339_REGEX.match(str_in) is None:
                msg = ('Date expected to conform to RFC3339. Read {}.'
                       .format(str_in))
                raise InvalidEntryError(msg)
            try:
                datetime.strptime(str_in, DateSpec.RFC3339_FORMAT)
            except ValueError as e:
                msg = 'Invalid date. Read {}.'.format(str_in)
                raise_from(InvalidEntryError(msg), e)

        else:
            msg = 'Unrecognised date format: {}.'.format(self.format)
            raise ValueError(msg)


class EnumSpec(FieldSpec):
    """ Represents a field that holds an enum.

        The finite collection of permitted values must be specified.

        :ivar values: The set of permitted values.
    """
    def __init__(self, **kwargs):
        # type: (...) -> None
        """ Make a HashingProperties object from keyword arguments.

            :param values: (optional) Value of `self.values`.
        """
        super().__init__(**kwargs)

        if 'values' in kwargs:
            self.values = kwargs['values']

    @classmethod
    def from_json_dict(cls, json_dict):
        # type: (Dict[str, Any]) -> EnumSpec
        """ Make a EnumSpec object from a dictionary containing its
            properties.

            The dictionary must contain `'enum'` key specifying the
            permitted values. In addition, it must contain a
            `'hashing'` key, whose contents are passed to
            HashingProperties.__init__.

            :param properties: The properties dictionary.
        """
        result = cast(EnumSpec,  # Appease the gods of Mypy.
                      super().from_json_dict(json_dict))

        format_ = json_dict['format']
        result.values = set(format_['values'])

        return result

    def validate(self, str_in):
        # type: (Text) -> None
        """ Validates an entry in the field.

            Raises `InvalidEntryError` iff the entry is invalid.

            An entry is invalid iff it is not one of the permitted
            values.

            :param str_in: String to validate.
            :raises InvalidEntryError: When entry is invalid.
        """
        super().validate(str_in)

        if str_in not in self.values:
            msg = ('Expected enum value is one of {}. Read {}.'
                   .format(self.values, str_in))
            raise InvalidEntryError(msg)


# Map type string (as defined in master schema) to
FIELD_TYPE_MAP = {
    'string': StringSpec,
    'integer': IntegerSpec,
    'date': DateSpec,
    'enum': EnumSpec,
}


def spec_from_json_dict(field_properties):
    # type: (Dict[str, Any]) -> FieldSpec
    """ Turns a dictionary into the appropriate object.

        :param field_properties: A dictionary with properties.
        :returns: An initialised instance of the appropriate FieldSpec
            subclass.
    """
    type_str = field_properties['format']['type']
    spec_type = FIELD_TYPE_MAP[type_str]
    return spec_type.from_json_dict(field_properties)
