# -*- coding: utf-8 -*-

""" Validate data inputs.

    Validates individual entries and the overall format against the
    specified schema.
"""

from future.utils import raise_from

from clkhash import field_formats


class EntryError(Exception):
    """ An entry is invalid.
    """
    pass


class FormatError(Exception):
    """ The format of the data is invalid.
    """
    pass


def validate_data(fields,  # type: Sequence[field_formats.FieldSpec]
                  data     # type: Sequence[Sequence[str]]
                  ):
    # type: (...) -> None
    """ Validate the `data` entries according to the specification in
        `fields`.

        :param fields: The `FieldSpec` objects forming the
            specification.
        :param data: The data to validate.
        :raises EntryError: When an entry is not valid according to its
            `FieldSpec`.
        :raises FormatError: When the number of entries in a row does
            not match expectation.
    """
    validators = [f.validate for f in fields]

    for row in data:
        if len(validators) != len(row):
            msg = 'Row has {} entries when {} are expected.'.format(
                len(row), len(validators))
            raise FormatError(msg)

        for entry, v in zip(row, validators):
            try:
                v(entry)
            except field_formats.InvalidEntryError as e:
                raise_from(EntryError('Invalid entry.'), e)


def validate_header(fields,       # type: Sequence[field_formats.FieldSpec]
                    column_names  # type: Sequence[str]
                    ):
    # type: (...) -> None
    """ Validate the `column_names` according to the specification in
        `fields`.

        :param fields: The `FieldSpec` objects forming the
            specification.
        :param data: The data to validate.
        :raises FormatError: When the number of columns or the column
            identifiers don't match the specification.
    """
    if len(fields) != len(column_names):
        msg = 'Header has {} columns when {} are expected'.format(
            len(column_names), len(fields))
        raise FormatError(msg)

    for f, column in zip(fields, column_names):
        if f.identifier != column:
            msg = "Column has identifier '{}' when '{}' is expected".format(
                column, f.identifier)
            raise FormatError(msg)
