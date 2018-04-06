# -*- coding: utf-8 -*-

""" Classes that specify the requirements for each column in a dataset.
    They take care of validation, and produce the settings required to
    perform the hashing.
"""

from __future__ import unicode_literals

import abc
from datetime import datetime
import re
from typing import Any, cast, Dict, Iterable, Optional, Text, Union

from future.builtins import super
from future.utils import raise_from
from six import add_metaclass

from clkhash.backports import re_compile_full


class InvalidEntryError(ValueError):
    """ An entry in the data file does not conform to the schema.
    """


class InvalidSchemaError(ValueError):
    """ The schema is not valid.

        This exception is raised if, for example, a regular expression
        included in the schema is not syntactically correct.
    """


class FieldHashingProperties(object):
    """ Stores the settings used to hash a field. This includes the
        encoding and tokenisation parameters.

        :ivar str encoding: The encoding to use when converting the
            string to bytes. Refer to
            `Python's documentation <https://docs.python.org/3/library/codecs.html#standard-encodings>`_
            for possible values.
        :ivar int ngram: The n in n-gram. Possible values are 0, 1, and
            2.
        :ivar bool positional: Controls whether the n-grams are
            positional.
        :ivar float weight: Controls the weight of the field in the
            Bloom filter.
    """
    _DEFAULT_ENCODING = 'utf-8'
    _DEFAULT_POSITIONAL = False
    _DEFAULT_WEIGHT = 1

    def __init__(self,
                 ngram,                          # type: int
                 encoding=_DEFAULT_ENCODING,     # type: str
                 weight=_DEFAULT_WEIGHT,         # type: Union[int, float]
                 positional=_DEFAULT_POSITIONAL  # type: bool
                 ):
        # type: (...) -> None
        """ Make a :class:`FieldHashingProperties` object, setting it
            attributes to values specified in keyword arguments.
        """
        if ngram not in range(3):
            msg = 'ngram is {} but is expected to be 0, 1, or 2.'
            raise ValueError(msg.format(ngram))

        try:
            ''.encode(encoding)
        except LookupError as e:
            msg = '{} is not a valid Python encoding.'
            raise_from(ValueError(msg.format(encoding)), e)

        if weight < 0:
            msg = 'weight should be non-negative but is {}.'
            raise ValueError(msg.format(weight))

        self.ngram = ngram
        self.encoding = encoding
        self.positional = positional
        self.weight = weight

    @classmethod
    def from_json_dict(cls, json_dict):
        # type: (Dict[str, Any]) -> FieldHashingProperties
        """ Make a :class:`FieldHashingProperties` object from a
            dictionary.

            :param dict json_dict:
                The dictionary must have have an 'ngram' key. It may have
                'positional' and 'weight' keys; if these are missing, then
                they are filled with the default values. The encoding is
                always set to the default value.
            :return: A :class:`FieldHashingProperties` instance.
        """
        return cls(
            ngram=json_dict['ngram'],
            positional=json_dict.get(
                'positional', FieldHashingProperties._DEFAULT_POSITIONAL),
            weight=json_dict.get(
                'weight', FieldHashingProperties._DEFAULT_WEIGHT))


@add_metaclass(abc.ABCMeta)
class FieldSpec(object):
    """ Abstract base class representing the specification of a column
        in the dataset. Subclasses validate entries, and modify the
        `hashing_properties  ivar to customise hashing procedures.

        :ivar str identifier: The name of the field.
        :ivar str description: Description of the field format.
        :ivar FieldHashingProperties hashing_properties: The properties
            for hashing.
    """
    def __init__(self,
                 identifier,          # type: str
                 hashing_properties,  # type: FieldHashingProperties
                 description=None     # type: Optional[str]
                 ):
        # type: (...) -> None
        """ Make a FieldSpec object, setting it attributes to values
            specified in keyword arguments.
        """
        self.identifier = identifier
        self.hashing_properties = hashing_properties
        self.description = description

    @classmethod
    def from_json_dict(cls, field_dict):
        # type: (Dict[str, Any]) -> FieldSpec
        """ Initialise a FieldSpec object from a dictionary of
            properties.

            :param dict field_dict: The properties dictionary to use. Must
                contain a `'hashing'` key that meets the requirements of
                :class:`FieldHashingProperties`. Subclasses may requrire
            :raises InvalidSchemaError: When the `properties`
                dictionary contains invalid values. Exactly what that
                means is decided by the subclasses.
        """
        identifier = field_dict['identifier']
        description = field_dict['format'].get('description')
        hashing_properties = FieldHashingProperties.from_json_dict(
            field_dict['hashing'])

        result = cls.__new__(cls)  # type: ignore
        result.identifier = identifier
        result.hashing_properties = hashing_properties
        result.description = description

        return result

    @abc.abstractmethod
    def validate(self, str_in):
        # type: (Text) -> None
        """ Validates an entry in the field.

            Raises :class:`InvalidEntryError` iff the entry is invalid.

            Subclasses must override this method with their own
            validation. They should call the parent's `validate` method
            via `super`.

            :param str str_in: String to validate.
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
        characters into bytes. This is stored in `hashing_properties`
        since it is needed for hashing.

        :ivar regex: Compiled regular expression that entries must
            conform to. Present only if the specification is regex-
            -based.
        :ivar str case: The casing of the entries. One of `'lower'`,
            `'upper'`, or `'mixed'`. Default is `'mixed'`. Present only
            if the specification is not regex-based.
        :ivar int min_length: The minimum length of the string. `None`
            if there is no minimum length. Present only if the
            specification is not regex-based.
        :ivar int max_length: The maximum length of the string. `None`
            if there is no maximum length. Present only if the
            specification is not regex-based.
    """
    _DEFAULT_CASE = 'mixed'
    _DEFAULT_MIN_LENGTH = 0
    _PERMITTED_CASE_STYLES = {'lower', 'upper', 'mixed'}

    def __init__(self,
                 identifier,                      # type: str
                 hashing_properties,              # type: FieldHashingProperties
                 description=None,                # type: str
                 regex=None,                      # type: Optional[str]
                 case=_DEFAULT_CASE,              # type: str
                 min_length=_DEFAULT_MIN_LENGTH,  # type: Optional[int]
                 max_length=None                  # type: Optional[int]
                 ):
        # type: (...) -> None
        """ Make a StringSpec object, setting it attributes to values
            specified in keyword arguments.
        """ 
        super().__init__(identifier=identifier,
                         description=description,
                         hashing_properties=hashing_properties)

        regex_based = regex is not None

        if regex_based and (case != self._DEFAULT_CASE
                            or min_length != self._DEFAULT_MIN_LENGTH
                            or max_length is not None):
            msg = ('regex cannot be passed along with case, min_length, or'
                   ' max_length.')
            raise ValueError(msg)

        if case not in self._PERMITTED_CASE_STYLES:
            msg = ("the case is {}, but should be 'lower', 'upper', or"
                   "'mixed'")
            raise ValueError(msg.format(case))

        if regex_based and min_length < 0:
            msg = ('min_length must be non-negative, but is {}')
            raise ValueError(msg.format(min_length))

        if regex_based and max_length is not None and max_length <= 0:
            msg = ('max_length must be positive, but is {}')
            raise ValueError(msg.format(max_length))

        if regex_based:
            try:
                compiled_regex = re_compile_full(regex)
            except (SyntaxError, re.error) as e:
                msg = "invalid regular expression '{}.'".format(regex)
                raise_from(InvalidSchemaError(msg), e)
            self.regex = compiled_regex
        else:
            self.case = case
            self.min_length = min_length
            self.max_length = max_length

        self.regex_based = regex_based

    @classmethod
    def from_json_dict(cls, json_dict):
        # type: (Dict[str, Any]) -> StringSpec
        """ Make a StringSpec object from a dictionary containing its
            properties.

            :param dict json_dict: This dictionary must contain an
                `'encoding'` key associated with a Python-conformant
                encoding. It must also contain a `'hashing'` key, whose
                contents are passed to :class:`FieldHashingProperties`.
                Permitted keys also include `'pattern'`, `'case'`,
                `'minLength'`, and `'maxLength'`.
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
            except (SyntaxError, re.error) as e:
                msg = "Invalid regular expression '{}.'".format(pattern)
                raise_from(InvalidSchemaError(msg), e)
            result.regex_based = True

        else:
            result.case = format_.get('case', StringSpec._DEFAULT_CASE)
            result.min_length = format_.get('minLength')
            result.max_length = format_.get('maxLength')
            result.regex_based = False

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

            :param str str_in: String to validate.
            :raises InvalidEntryError: When entry is invalid.
            :raises ValueError: When self.case is not one of the
                permitted values (`'lower'`, `'upper'`, or `'mixed'`).
        """
        super().validate(str_in)  # Validate encoding.

        if self.regex_based:
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

        :ivar int minimum: The minimum permitted value.
        :ivar int maximum: The maximum permitted value or None.
    """

    _DEFAULT_MINIMUM = 0

    def __init__(self,
                 identifier,                # type: str
                 hashing_properties,        # type: FieldHashingProperties
                 description=None,          # type: str
                 minimum=_DEFAULT_MINIMUM,  # int
                 maximum=None,              # Optional[int]
                 **kwargs                   # Dict[str, Any]
                 ):
        # type: (...) -> None
        """ Make a IntegerSpec object, setting it attributes to values
            specified in keyword arguments.
        """
        super().__init__(identifier=identifier,
                         description=description,
                         hashing_properties=hashing_properties)

        self.minimum = minimum
        self.maximum = maximum

    @classmethod
    def from_json_dict(cls, json_dict):
        # type: (Dict[str, Any]) -> IntegerSpec
        """ Make a IntegerSpec object from a dictionary containing its
            properties.

            :param dict json_dict: This dictionary may contain
                `'minimum'` and `'maximum'` keys. In addition, it must
                contain a `'hashing'` key, whose contents are passed to
                :class:`FieldHashingProperties`.

            :param dict json_dict: The properties dictionary.
        """
        result = cast(IntegerSpec,  # For Mypy.
                      super().from_json_dict(json_dict))

        format_ = json_dict['format']
        result.minimum = format_.get('minimum', cls._DEFAULT_MINIMUM)
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

            :param str str_in: String to validate.
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

       Dates are specified as full-dates as defined in
       `RFC3339 <https://tools.ietf.org/html/rfc3339>`_ E.g.,
       ``1996-12-19``

        :ivar str format: The format of the date.
    """
    _PERMITTED_FORMATS = {'rfc3339'}
    _RFC3339_REGEX = re_compile_full(r'\d\d\d\d-\d\d-\d\d')
    _RFC3339_FORMAT = '%Y-%m-%d'

    def __init__(self,
                 identifier,          # type: str
                 hashing_properties,  # type: FieldHashingProperties
                 format,              # type: str
                 description=None     # type: str
                 ):
        # type: (...) -> None
        """ Make a DateSpec object, setting it attributes to values
            specified in keyword arguments.
        """
        super().__init__(identifier=identifier,
                         description=description,
                         hashing_properties=hashing_properties)

        if format not in self._PERMITTED_FORMATS:
            msg = 'No validation for date format: {}.'.format(format)
            raise NotImplementedError(msg)

        self.format = format

    @classmethod
    def from_json_dict(cls, json_dict):
        # type: (Dict[str, Any]) -> DateSpec
        """ Make a DateSpec object from a dictionary containing its
            properties.

            :param dict json_dict: This dictionary must contain a
                `'format'` key. In addition, it must contain a
                `'hashing'` key, whose contents are passed to
                :class:`FieldHashingProperties`.

            :param json_dict: The properties dictionary.
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

            :param str str_in: String to validate.
            :raises InvalidEntryError: Iff entry is invalid.
            :raises ValueError: When self.format is unrecognised.
        """
        super().validate(str_in)

        if self.format == 'rfc3339':
            if self._RFC3339_REGEX.match(str_in) is None:
                msg = ('Date expected to conform to RFC3339. Read {}.'
                       .format(str_in))
                raise InvalidEntryError(msg)
            try:
                datetime.strptime(str_in, self._RFC3339_FORMAT)
            except ValueError as e:
                msg = 'Invalid date. Read {}.'.format(str_in)
                raise_from(InvalidEntryError(msg), e)

        else:
            msg = 'No validation for date format: {}.'.format(self.format)
            raise NotImplementedError(msg)


class EnumSpec(FieldSpec):
    """ Represents a field that holds an enum.

        The finite collection of permitted values must be specified.

        :ivar values: The set of permitted values.
    """
    def __init__(self,
                 identifier,          # type: str
                 hashing_properties,  # type: FieldHashingProperties
                 values,              # type: Iterable[str]
                 description=None     # type: str
                 ):
        # type: (...) -> None
        """ Make a EnumSpec object, setting it attributes to values
            specified in keyword arguments.
        """
        super().__init__(identifier=identifier,
                         description=description,
                         hashing_properties=hashing_properties)

        self.values = set(values)

    @classmethod
    def from_json_dict(cls, json_dict):
        # type: (Dict[str, Any]) -> EnumSpec
        """ Make a EnumSpec object from a dictionary containing its
            properties.

            :param dict json_dict: This dictionary must contain an
                `'enum'` key specifying the permitted values. In
                addition, it must contain a `'hashing'` key, whose
                contents are passed to :class:`FieldHashingProperties`.
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

            :param str str_in: String to validate.
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


def spec_from_json_dict(json_dict):
    # type: (Dict[str, Any]) -> FieldSpec
    """ Turns a dictionary into the appropriate object.

        :param dict json_dict: A dictionary with properties.
        :returns: An initialised instance of the appropriate FieldSpec
            subclass.
    """
    type_str = json_dict['format']['type']
    spec_type = cast(FieldSpec, FIELD_TYPE_MAP[type_str])
    return spec_type.from_json_dict(json_dict)
