# -*- coding: utf-8 -*-

""" Classes that specify the requirements for each column in a dataset.
    They take care of validation, and produce the settings required to
    perform the hashing.
"""

from __future__ import unicode_literals

import abc
import re
from datetime import datetime
from typing import Any, Dict, Iterable, Optional, Text, cast

from future.builtins import range, super
from six import add_metaclass

from clkhash.backports import raise_from, re_compile_full, strftime


class InvalidEntryError(ValueError):
    """ An entry in the data file does not conform to the schema.
    """
    field_spec = None  # type: Optional[FieldSpec]


class InvalidSchemaError(ValueError):
    """ The schema is not valid.

        This exception is raised if, for example, a regular expression
        included in the schema is not syntactically correct.
    """


class MissingValueSpec(object):
    """ Stores the information about how to find and treat missing
        values.

        :ivar str sentinel: sentinel is the string that identifies a
        missing value e.g.: 'N/A', ''.
        The sentinel will not be validated against the
        feature format definition
        :ivar str replaceWith: defines the string which replaces the
        sentinel whenever present, can be 'None', then sentinel will
         not be replaced.
    """

    def __init__(self,
                 sentinel,  # type: str
                 replace_with=None  # type: Optional[str]
                 ):
        # type: (...) -> None
        self.sentinel = sentinel
        self.replace_with = (replace_with if replace_with is not None
                             else sentinel)

    @classmethod
    def from_json_dict(cls, json_dict):
        # type: (Dict[str, Any]) -> MissingValueSpec
        return cls(
            sentinel=json_dict['sentinel'],
            replace_with=cast(Optional[str], json_dict.get('replaceWith'))
        )


class FieldHashingProperties(object):
    """
    Stores the settings used to hash a field.

    This includes the encoding and tokenisation parameters.

        :ivar str encoding: The encoding to use when converting the
            string to bytes. Refer to
            `Python's documentation <https://docs.python.org/3/library/codecs.html#standard-encodings>`
            for possible values.
        :ivar int ngram: The n in n-gram. Possible values are 0, 1, and
            2.
        :ivar bool positional: Controls whether the n-grams are
            positional.
        :ivar int num_bits: dynamic k = num_bits / number of n-grams
        :ivar int k: max number of bits per n-gram
    """
    _DEFAULT_ENCODING = 'utf-8'
    _DEFAULT_POSITIONAL = False

    def __init__(self,
                 ngram,  # type: int
                 encoding=_DEFAULT_ENCODING,      # type: str
                 positional=_DEFAULT_POSITIONAL,  # type: bool
                 hash_type='blakeHash',           # type: str
                 prevent_singularity=None,        # type: Optional[bool]
                 num_bits=None,                   # type: Optional[int]
                 k=None,                          # type: Optional[int]
                 missing_value=None               # type: Optional[MissingValueSpec]
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

        if prevent_singularity is not None and hash_type != 'doubleHash':
            raise ValueError("Prevent_singularity must only be specified"
                             " with hash_type doubleHash.")

        if not num_bits and not k:
            raise ValueError('One of num_bits or k must be specified.')

        self.ngram = ngram
        self.encoding = encoding
        self.positional = positional
        self.hash_type = hash_type
        self.prevent_singularity = prevent_singularity
        self.num_bits = num_bits
        self.k = k
        self.missing_value = missing_value

    def ks(self, num_ngrams):
        # type (int) -> [int]
        """
        Provide a k for each ngram in the field value.
        :param num_ngrams: number of ngrams in the field value
        :return: [ k, ... ] a k value for each of num_ngrams such that the sum is exactly num_bits
        """
        if self.num_bits:
            k = int(self.num_bits / num_ngrams)
            residue = self.num_bits % num_ngrams
            return ([k + 1] * residue) + ([k] * (num_ngrams - residue))
        else:
            return [self.k if self.k else 0] * num_ngrams

    def replace_missing_value(self, str_in):
        # type: (Text) -> Text
        """ returns 'str_in' if it is not equals to the 'sentinel' as
        defined in the missingValue section of
        the schema. Else it will return the 'replaceWith' value.

        :param str_in:
        :return: str_in or the missingValue replacement value
        """
        if self.missing_value is None:
            return str_in
        elif self.missing_value.sentinel == str_in:
            return self.missing_value.replace_with
        else:
            return str_in


def fhp_from_json_dict(
        json_dict  # type: Dict[str, Any]
    ):
    # type: (...) -> FieldHashingProperties
    """
    Make a :class:`FieldHashingProperties` object from a dictionary.

        :param dict json_dict:
            The dictionary must have have an 'ngram' key
            and one of k or num_bits. It may have
            'positional' key; if missing a default is used.
            The encoding is
            always set to the default value.
        :return: A :class:`FieldHashingProperties` instance.
    """
    h = json_dict.get('hash', {'type': 'blakeHash'})
    num_bits = json_dict.get('numBits')
    k = json_dict.get('k')
    if not num_bits and not k:
        num_bits = 200 # default for v2 schema
    return FieldHashingProperties(
        ngram=json_dict['ngram'],
        positional=json_dict.get(
            'positional', FieldHashingProperties._DEFAULT_POSITIONAL),
        hash_type=h['type'],
        prevent_singularity=h.get('prevent_singularity'),
        num_bits=num_bits,
        k=k,
        missing_value=MissingValueSpec.from_json_dict(
            json_dict[
                'missingValue']) if 'missingValue' in json_dict else None
    )


@add_metaclass(abc.ABCMeta)
class FieldSpec(object):
    """ Abstract base class representing the specification of a column
        in the dataset. Subclasses validate entries, and modify the
        `hashing_properties`  ivar to customise hashing procedures.

        :ivar str identifier: The name of the field.
        :ivar str description: Description of the field format.
        :ivar FieldHashingProperties hashing_properties: The properties
            for hashing. None if field ignored.
    """

    def __init__(self,
                 identifier,  # type: str
                 hashing_properties,  # type: Optional[FieldHashingProperties]
                 description=None  # type: Optional[str]
                 ):
        # type: (...) -> None
        """ Make a FieldSpec object, setting it attributes to values
            specified in keyword arguments.
        """
        self.identifier = identifier
        self.hashing_properties = hashing_properties
        self.description = description

    @classmethod
    def from_json_dict(cls,
                       field_dict  # type: Dict[str, Any]
                       ):
        # type: (...) -> FieldSpec
        """ Initialise a FieldSpec object from a dictionary of
            properties.

            :param dict field_dict: The properties dictionary to use. Must
                contain a `'hashing'` key that meets the requirements of
                :class:`FieldHashingProperties`. Subclasses may require
            :raises InvalidSchemaError: When the `properties`
                dictionary contains invalid values. Exactly what that
                means is decided by the subclasses.
        """
        identifier = field_dict['identifier']
        description = field_dict['format'].get('description')
        hashing_properties = fhp_from_json_dict(field_dict['hashing']) if 'hashing' in field_dict else None

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
        if self.hashing_properties:  # else its Ignore
            try:
                str_in.encode(encoding=self.hashing_properties.encoding)
            except UnicodeEncodeError as err:
                msg = ("Expected entry that can be encoded in {}. Read '{}'."
                       .format(self.hashing_properties.encoding, str_in))
                e_new = InvalidEntryError(msg)
                e_new.field_spec = self
                raise_from(e_new, err)


    def is_missing_value(self, str_in):
        # type: (Text) -> bool
        """ tests if 'str_in' is the sentinel value for this field

            :param str str_in: String to test if it stands for missing value
            :return: True if a missing value is defined for this field and
            str_in matches this value

        """
        return (self.hashing_properties is not None and
            self.hashing_properties.missing_value is not None and
            self.hashing_properties.missing_value.sentinel == str_in)

    def format_value(self, str_in):
        # type: (Text) -> Text
        """ formats the value 'str_in' for hashing according to this field's
        spec.

            There are several reasons why this might be necessary:

            1. This field contains missing values which have to be replaced
            by some other string
            2. There are several different ways to describe a specific value
            for this field, e.g.: all of '+65', ' 65',
               '65' are valid representations of the integer 65.
            3. Entries of this field might contain elements with no entropy,
            e.g. dates might be formatted as
               yyyy-mm-dd, thus all dates will have '-' at the same place.
               These artifacts have no value for entity
               resolution and should be removed.

            :param str str_in: the string to format
            :return: a string representation of 'str_in' which is ready to
            be hashed
        """
        if self.hashing_properties and self.is_missing_value(str_in):
            return self.hashing_properties.replace_missing_value(str_in)
        else:
            return self._format_regular_value(str_in)

    def _format_regular_value(self, str_in):
        # type: (Text) -> Text
        """ overwrite this if you want to modify 'str_in' before hashing.

            :param str_in:
            :return: a string representation of 'str_in' which is ready to
            be hashed
        """
        return str_in


class StringSpec(FieldSpec):
    """ Represents a field that holds strings.

        One way to specify the format of the entries is to provide a
        regular expression that they must conform to. Another is to
        provide zero or more of: minimum length, maximum length, casing
        (lower, upper, mixed).

        Each string field also specifies an encoding used when turning
        characters into bytes. This is stored in `hashing_properties`
        since it is needed for hashing.

        :ivar str encoding: The encoding to use when converting the
            string to bytes. Refer to
            `Python's documentation
            <https://docs.python.org/3/library/codecs.html#standard
            -encodings>`_
            for possible values.
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
                 identifier,  # type: str
                 hashing_properties,  # type: FieldHashingProperties
                 description=None,  # type: Optional[str]
                 regex=None,  # type: Optional[str]
                 case=_DEFAULT_CASE,  # type: str
                 min_length=_DEFAULT_MIN_LENGTH,  # type: int
                 max_length=None  # type: Optional[int]
                 ):
        # type: (...) -> None
        """ Make a StringSpec object, setting it attributes to values
            specified in keyword arguments.
        """
        # noinspection PyCompatibility,PyArgumentList
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

        if min_length < 0:
            msg = 'min_length must be non-negative, but is {}'
            raise ValueError(msg.format(min_length))

        # type checker thinks max_length is of type None
        # noinspection PyTypeChecker
        if max_length is not None and max_length <= 0:
            msg = 'max_length must be positive, but is {}'
            raise ValueError(msg.format(max_length))

        if regex_based:
            regex_str = cast(str, regex)
            try:
                compiled_regex = re_compile_full(regex_str)
                self.regex = compiled_regex
            except (SyntaxError, re.error) as e:
                msg = "invalid regular expression '{}.'".format(regex_str)
                e_new = InvalidEntryError(msg)
                e_new.field_spec = self
                raise_from(e_new, e)
        else:
            self.case = case
            self.min_length = min_length
            self.max_length = max_length

        self.regex_based = regex_based

    @classmethod
    def from_json_dict(cls,
                       json_dict  # type: Dict[str, Any]
                       ):
        # type: (...) -> StringSpec
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
        # noinspection PyCompatibility
        result = cast(StringSpec,  # Go away, Mypy.
                      super().from_json_dict(json_dict))

        format_ = json_dict['format']
        if 'encoding' in format_ and result.hashing_properties:
            result.hashing_properties.encoding = format_['encoding']

        if 'pattern' in format_:
            pattern = format_['pattern']
            try:
                result.regex = re_compile_full(pattern)
            except (SyntaxError, re.error) as e:
                msg = "Invalid regular expression '{}.'".format(pattern)
                e_new = InvalidSchemaError(msg)
                raise_from(e_new, e)
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
        if self.is_missing_value(str_in):
            return
        # noinspection PyCompatibility
        super().validate(str_in)  # Validate encoding.

        if self.regex_based:
            match = self.regex.match(str_in)
            if match is None:
                e = InvalidEntryError(
                    'Expected entry that conforms to regular expression '
                    "'{}'. Read '{}'.".format(self.regex.pattern, str_in))
                e.field_spec = self
                raise e

        else:
            str_len = len(str_in)
            if self.min_length is not None and str_len < self.min_length:
                e = InvalidEntryError(
                    "Expected string length of at least {}. Read string '{}' "
                    'of length {}.'.format(self.min_length, str_in, str_len))
                e.field_spec = self
                raise e

            if self.max_length is not None and str_len > self.max_length:
                e = InvalidEntryError(
                    "Expected string length of at most {}. Read string '{}' "
                    'of length {}.'.format(self.max_length, str_in, str_len))
                e.field_spec = self
                raise e

            if self.case == 'upper':
                if str_in.upper() != str_in:
                    msg = "Expected upper case string. Read '{}'.".format(
                        str_in)
                    e = InvalidEntryError(msg)
                    e.field_spec = self
                    raise e
            elif self.case == 'lower':
                if str_in.lower() != str_in:
                    msg = "Expected lower case string. Read '{}'.".format(
                        str_in)
                    e = InvalidEntryError(msg)
                    e.field_spec = self
                    raise e
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

    def __init__(self,
                 identifier,  # type: str
                 hashing_properties,  # type: FieldHashingProperties
                 description=None,  # type: Optional[str]
                 minimum=None,  # type: Optional[int]
                 maximum=None,  # type: Optional[int]
                 **kwargs  # type: Dict[str, Any]
                 ):
        # type: (...) -> None
        """ Make a IntegerSpec object, setting it attributes to values
            specified in keyword arguments.
        """
        # noinspection PyCompatibility,PyArgumentList
        super().__init__(identifier=identifier,
                         description=description,
                         hashing_properties=hashing_properties)

        self.minimum = minimum
        self.maximum = maximum

    @classmethod
    def from_json_dict(cls,
                       json_dict  # type: Dict[str, Any]
                       ):
        # type: (...) -> IntegerSpec
        """ Make a IntegerSpec object from a dictionary containing its
            properties.

            :param dict json_dict: This dictionary may contain
                `'minimum'` and `'maximum'` keys. In addition, it must
                contain a `'hashing'` key, whose contents are passed to
                :class:`FieldHashingProperties`.

            :param dict json_dict: The properties dictionary.
        """
        # noinspection PyCompatibility
        result = cast(IntegerSpec,  # For Mypy.
                      super().from_json_dict(json_dict))

        format_ = json_dict['format']
        result.minimum = format_.get('minimum')
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
        if self.is_missing_value(str_in):
            return
        # noinspection PyCompatibility
        super().validate(str_in)

        try:
            value = int(str_in, base=10)
        except ValueError as e:
            msg = "Invalid integer. Read '{}'.".format(str_in)
            e_new = InvalidEntryError(msg)
            e_new.field_spec = self
            raise_from(e_new, e)
            return  # to stop PyCharm thinking that value might be undefined
            #  later

        if self.minimum is not None and value < self.minimum:
            msg = ("Expected integer value of at least {}. Read '{}'."
                   .format(self.minimum, value))
            e_new = InvalidEntryError(msg)
            e_new.field_spec = self
            raise e_new

        if self.maximum is not None and value > self.maximum:
            msg = ("Expected integer value of at most {}. Read '{}'."
                   .format(self.maximum, value))
            e_new = InvalidEntryError(msg)
            e_new.field_spec = self
            raise e_new

    def _format_regular_value(self, str_in):
        # type: (Text) -> Text
        """ we need to reformat integer strings, as there can be different
        strings for the same integer. The
            strategy of unification here is to first parse the integer
            string to an Integer type. Thus all of
            '+13', ' 13', '13' will be parsed to 13. We then convert the
            integer value to an unambiguous string
            (no whitespaces, leading '-' for negative numbers, no leading '+').

            :param str_in: integer string
            :return: integer string without whitespaces, leading '-' for
            negative numbers, no leading '+'
        """
        try:
            value = int(str_in, base=10)
            return str(value)
        except ValueError as e:
            msg = "Invalid integer. Read '{}'.".format(str_in)
            e_new = InvalidEntryError(msg)
            e_new.field_spec = self
            raise_from(e_new, e)


class DateSpec(FieldSpec):
    """ Represents a field that holds dates.

       Dates are specified as full-dates in a format that can be described
       as a *strptime()* (C89 standard) compatible
       format string.
       E.g.: the format for the standard internet format `RFC3339
       <https://tools.ietf.org/html/rfc3339>`_
       (e.g. 1996-12-19) is '%Y-%m-%d'.

        :ivar str format: The format of the date.
    """
    OUTPUT_FORMAT = '%Y%m%d'

    def __init__(self,
                 identifier,  # type: str
                 hashing_properties,  # type: FieldHashingProperties
                 format,  # type: str
                 description=None  # type: Optional[str]
                 ):
        # type: (...) -> None
        """ Make a DateSpec object, setting it attributes to values
            specified in keyword arguments.
        """
        # noinspection PyCompatibility,PyArgumentList
        super().__init__(identifier=identifier,
                         description=description,
                         hashing_properties=hashing_properties)

        self.format = format

    @classmethod
    def from_json_dict(cls,
                       json_dict  # type: Dict[str, Any]
    ):
        # type: (...) -> DateSpec
        """ Make a DateSpec object from a dictionary containing its
            properties.

            :param dict json_dict: This dictionary must contain a
                `'format'` key. In addition, it must contain a
                `'hashing'` key, whose contents are passed to
                :class:`FieldHashingProperties`.

            :param json_dict: The properties dictionary.
        """
        # noinspection PyCompatibility
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
        if self.is_missing_value(str_in):
            return
        # noinspection PyCompatibility
        super().validate(str_in)
        try:
            datetime.strptime(str_in, self.format)
        except ValueError as e:
            msg = "Validation error for date type: {}".format(e)
            e_new = InvalidEntryError(msg)
            e_new.field_spec = self
            raise_from(e_new, e)

    def _format_regular_value(self, str_in):
        # type: (Text) -> Text
        """ we overwrite default behaviour as we want to hash the numbers
        only, no fillers like '-', or '/'

        :param str str_in: date string
        :return: str date string with format DateSpec.OUTPUT_FORMAT
        """
        try:
            dt = datetime.strptime(str_in, self.format)
            return strftime(dt, DateSpec.OUTPUT_FORMAT)
        except ValueError as e:
            msg = "Unable to format date value '{}'. Reason: {}".format(str_in,
                                                                        e)
            e_new = InvalidEntryError(msg)
            e_new.field_spec = self
            raise_from(e_new, e)


class EnumSpec(FieldSpec):
    """ Represents a field that holds an enum.

        The finite collection of permitted values must be specified.

        :ivar values: The set of permitted values.
    """

    def __init__(self,
                 identifier,  # type: str
                 hashing_properties,  # type: FieldHashingProperties
                 values,  # type: Iterable[str]
                 description=None  # type: Optional[str]
                 ):
        # type: (...) -> None
        """ Make a EnumSpec object, setting it attributes to values
            specified in keyword arguments.
        """
        # noinspection PyCompatibility,PyArgumentList
        super().__init__(identifier=identifier,
                         description=description,
                         hashing_properties=hashing_properties)

        self.values = set(values)

    @classmethod
    def from_json_dict(cls,
                       json_dict  # type: Dict[str, Any]
                       ):
        # type: (...) -> EnumSpec
        """ Make a EnumSpec object from a dictionary containing its
            properties.

            :param dict json_dict: This dictionary must contain an
                `'enum'` key specifying the permitted values. In
                addition, it must contain a `'hashing'` key, whose
                contents are passed to :class:`FieldHashingProperties`.
        """
        # noinspection PyCompatibility
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
        if self.is_missing_value(str_in):
            return
        # noinspection PyCompatibility
        super().validate(str_in)

        if str_in not in self.values:
            msg = ("Expected enum value to be one of {}. Read '{}'."
                   .format(list(self.values), str_in))
            e = InvalidEntryError(msg)
            e.field_spec = self
            raise e


class Ignore(FieldSpec):
    """
    represent a field which will be ignored throughout the clk processing.
    """

    def __init__(self,
                 identifier=None  # type: Optional[str]
                 ):
        # type: (...) -> None
        # noinspection PyCompatibility
        super().__init__('' if identifier is None else identifier,
                         None)

    def validate(self, str_in):
        pass


# Map type string (as defined in master schema) to
FIELD_TYPE_MAP = {
    'string': StringSpec,
    'integer': IntegerSpec,
    'date': DateSpec,
    'enum': EnumSpec,
}


def spec_from_json_dict(
        json_dict  # type: Dict[str, Any]
):
    # type: (...) -> FieldSpec
    """ Turns a dictionary into the appropriate object.

        :param dict json_dict: A dictionary with properties.
        :returns: An initialised instance of the appropriate FieldSpec
            subclass.
    """
    if 'ignored' in json_dict:
        return Ignore(json_dict['identifier'])
    type_str = json_dict['format']['type']
    spec_type = cast(FieldSpec, FIELD_TYPE_MAP[type_str])
    return spec_type.from_json_dict(json_dict)
