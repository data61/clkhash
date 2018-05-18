# -*- coding: utf-8 -*-

""" Validate data inputs.

    Validates individual entries and the overall format against the
    specified schema.
"""

from typing import cast, Optional, Sequence

from future.builtins import zip

from clkhash.backports import raise_from
from clkhash.field_formats import (FieldSpec, InvalidEntryError)


class EntryError(ValueError):
    """ An entry is invalid.
    """
    row_index = None  # type: Optional[int]
    field_spec = None  # type: Optional[FieldSpec]


class FormatError(ValueError):
    """ The format of the data is invalid.
    """
    row_index = None  # type: Optional[int]


def validate_row_lengths(fields,  # type: Sequence[FieldSpec]
                         data  # type: Sequence[Sequence[str]]
                         ):
    # type: (...) -> None
    """ Validate the `data` row lengths according to the specification
        in `fields`.

        :param fields: The `FieldSpec` objects forming the
            specification.
        :param data: The rows to check.
        :raises FormatError: When the number of entries in a row does
            not match expectation.
    """
    for i, row in enumerate(data):
        if len(fields) != len(row):
            msg = 'Row {} has {} entries when {} are expected.'.format(
                i, len(row), len(fields))
            raise FormatError(msg)


def validate_entries(fields,  # type: Sequence[FieldSpec]
                     data  # type: Sequence[Sequence[str]]
                     ):
    # type: (...) -> None
    """ Validate the `data` entries according to the specification in
        `fields`.

        :param fields: The `FieldSpec` objects forming the
            specification.
        :param data: The data to validate.
        :raises EntryError: When an entry is not valid according to its
            :class:`FieldSpec`.
    """
    validators = [f.validate for f in fields]

    for i, row in enumerate(data):
        for entry, v in zip(row, validators):
            try:
                v(entry)
            except InvalidEntryError as e:
                msg = (
                    'Invalid entry in row {row_index}, column '
                    "'{column_name}'. {original_message}"
                ).format(
                    row_index=i,
                    column_name=cast(FieldSpec, e.field_spec).identifier,
                    original_message=e.args[0])
                e_invalid_entry = EntryError(msg)
                e_invalid_entry.field_spec = e.field_spec
                e_invalid_entry.row_index = i
                raise_from(e_invalid_entry, e)


def validate_header(fields,  # type: Sequence[FieldSpec]
                    column_names  # type: Sequence[str]
                    ):
    # type: (...) -> None
    """ Validate the `column_names` according to the specification in
        `fields`.

        :param fields: The `FieldSpec` objects forming the
            specification.
        :param column_names: A sequence of column identifier.
        :raises FormatError: When the number of columns or the column
            identifiers don't match the specification.
    """
    if len(fields) != len(column_names):
        msg = 'Header has {} columns when {} are expected.'.format(
            len(column_names), len(fields))
        raise FormatError(msg)

    for f, column in zip(fields, column_names):
        if f.identifier != column:
            msg = "Column has identifier '{}' when '{}' is expected.".format(
                column, f.identifier)
            raise FormatError(msg)
