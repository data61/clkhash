# -*- coding: utf-8 -*-

""" Schema loading and validation.
"""

from __future__ import unicode_literals

import base64
import json
import pkgutil
from typing import Any, Dict, Hashable, List, Text, TextIO

from future.utils import raise_from
import jsonschema

from clkhash.field_formats import FieldSpec, spec_from_json_dict


MASTER_SCHEMA_FILE_NAMES = {1: 'v1.json'}  # type: Dict[Hashable, Text]


class GlobalHashingProperties(object):
    """ Stores global hashing properties.

        :param k: The number of bits of the hash to set per ngram.
        :param l: The length of the resulting hash in bits. This is the
            length after XOR folding.
        :param xor_folds: The number of XOR folds to perform on the hash.
        :param hash_type: The hashing function to use. Choices are
            'doubleHash' and 'blakeHash'.
        :param hash_prevent_singularity: Ignored unless hash_type is
            'doubleHash'. Prevents bloom filter collisions in certain
            cases when True.
        :param kdf_type: The key derivation function to use. Currently,
            the only permitted value is 'HKDF'.
        :param kdf_hash: The hash function to use in key derivation. The
            options are 'SHA256' and 'SHA512'.
        :param kdf_info: The info for key derivation. See documentation
            of `HKDFconfig` for details.
        :param kdf_salt: The salt for key derivation. See documentation
            of `HKDFconfig` for details.
        :param kdf_key_size: The size of the derived keys in bytes.

    """
    __slots__ = ('k', 'l', 'xor_folds', 'hash_type',
                 'hash_prevent_singularity', 'kdf_type', 'kdf_hash',
                 'kdf_info', 'kdf_salt', 'kdf_key_size')

    def __init__(self, **kwargs):
        # type: (...) -> None
        """ Make a GlobalHashingProperties object from keyword
            arguments.

            :param k: Value of `self.k`.
            :param l: Value of `self.l`.
            :param xor_folds: Value of `self.xor_folds`.
            :param hash_type: Value of `self.hash_type`.
            :param hash_prevent_singularity: Value of `self.hash_prevent_singularity`.
            :param kdf_type: Value of `self.kdf_type`.
            :param kdf_hash: Value of `self.kdf_hash`.
            :param kdf_info: Value of `self.kdf_info`.
            :param kdf_salt: Value of `self.kdf_salt`.
            :param kdf_key_size: Value of `self.kdf_key_size`.

        """
        if 'k' in kwargs:
            self.k = kwargs['k']
        if 'l' in kwargs:
            self.l = kwargs['l']
        if 'xor_folds' in kwargs:
            self.xor_folds = kwargs['xor_folds']

        if 'hash_type' in kwargs:
            self.hash_type = kwargs['hash_type']
        if 'hash_prevent_singularity' in kwargs:
            self.hash_prevent_singularity = kwargs['hash_prevent_singularity']

        if 'kdf_type' in kwargs:
            self.kdf_type = kwargs['kdf_type']
        if 'kdf_hash' in kwargs:
            self.kdf_hash = kwargs['kdf_hash']
        if 'kdf_info' in kwargs:
            self.kdf_info = kwargs['kdf_info']
        if 'kdf_salt' in kwargs:
            self.kdf_salt = kwargs['kdf_salt']
        if 'kdf_key_size' in kwargs:
            self.kdf_key_size = kwargs['kdf_key_size']


    @classmethod
    def from_json_dict(cls, properties_dict):
        # type: (Dict[str, Any]) -> GlobalHashingProperties
        """ Make a GlobalHashingProperties object from a dictionary.

            :param properties_dict:
                The dictionary must have a `'type'` key and a `'config'`
                key. The `'config'` key must map to a dictionary
                containing a `'kdf'` key, which itself maps to a
                dictionary. That dictionary must have `'type'`, `'hash'`,
                `'keySize'`, `'salt'`, and `'type'` keys.
            :return: The resulting :class:`GlobalHashingProperties` object.
        """
        result = cls()

        result.k = properties_dict['k']
        result.l = properties_dict['l']
        result.xor_folds = properties_dict.get('xor_folds', 0)

        result.hash_type = properties_dict['hash']['type']
        result.hash_prevent_singularity = properties_dict['hash'].get(
            'prevent_singularity')

        result.kdf_type = properties_dict['kdf']['type']
        result.kdf_hash = properties_dict['kdf']['hash']
        result.kdf_info = base64.b64decode(
            properties_dict['kdf']['info'])
        result.kdf_salt = base64.b64decode(
            properties_dict['kdf']['salt'])
        result.kdf_key_size = properties_dict['kdf']['keySize']

        return result


class Schema(object):
    """ Overall schema which describes how to hash plaintext identifiers into clks

        :ivar version: Version for the schema. Needed to keep behaviour
            consistent between clkhash versions for the same schema.
        :ivar hashing_globals: Configuration affecting hashing of all fields. For example
            cryptographic salt material, bloom filter length.
        :ivar fields: Information and configuration specific to each field. For example
            how to validate and tokenize a phone number.
    """
    __slots__ = ('version', 'hashing_globals', 'fields')

    def __init__(self, version, hashing_globals, fields):
        # type: (str, GlobalHashingProperties, List[FieldSpec]) -> None

        self.version = version
        self.hashing_globals = hashing_globals
        self.fields = fields

    def __repr__(self):
        return "<Schema (v{}): {} fields>".format(self.version, len(self.fields))

    @classmethod
    def from_json_dict(cls, schema_dict, validate=True):
        # type: (Dict[str, Any], bool) -> Schema
        """ Make a Schema object from a dictionary.

            The dictionary must have a `'features'` key specifying the
            columns of the dataset. It must have a `'version'` key
            containing the master schema version that this schema
            conforms to. It must have a `'hash'` key with all the
            globals.

            :param schema_dict: The dictionary to use.
            :param validate: (default True) Raise an exception if the
                schema does not conform to the master schema.
            :return: The resulting :class:`Schema` object.
        """
        if validate:
            # This raises iff the schema is invalid.
            validate_schema_dict(schema_dict)

        hash_properties = GlobalHashingProperties.from_json_dict(schema_dict['clkConfig'])
        features = schema_dict['features']
        return cls(
            schema_dict['version'],
            hash_properties,
            list(map(spec_from_json_dict, features))
        )


def get_master_schema_(version):
    # type: (Hashable) -> bytes
    """ Loads the master schema of given version as bytes.

        :param version: The version of the master schema whose path we
            wish to retrieve.
        :raises SchemaError: When the schema version is unknown. This
            usually means that either (a) clkhash is out of date, or (b)
            the schema version listed is incorrect.
        :return: Bytes of the schema.
    """
    try:
        file_name = MASTER_SCHEMA_FILE_NAMES[version]
    except (TypeError, KeyError) as e:
        msg = ('Schema version {} is not supported. '
               'Consider updating clkhash.').format(version)
        raise_from(SchemaError(msg), e)

    try:
        schema_bytes = pkgutil.get_data('clkhash',
            'master-schemas/{}'.format(file_name))
    except IOError as e:  # In Python 3 we can be more specific with
                          # FileNotFoundError, but that doesn't exist in
                          # Python 2.
        msg = ('The master schema could not be found. The schema cannot be '
               'validated. Please file a bug report.')
        raise_from(MasterSchemaError(msg), e)
    
    if schema_bytes is None:
        msg = ('The master schema could not be loaded. The schema cannot be '
               'validated. Please file a bug report.')
        raise MasterSchemaError(msg)

    return schema_bytes


class SchemaError(Exception):
    """ The user-defined schema is invalid.
    """


class MasterSchemaError(Exception):
    """ Master schema missing? Corrupted? Otherwise surprising? This is
        the exception for you!
    """


def validate_schema_dict(schema):
    # type: (Dict[str, Any]) -> None
    """ Validate the schema.

        This raises iff either the schema or the master schema are
        invalid. If it's successful, it returns nothing.

        :param schema: The schema to validate, as parsed by `json`.
        :raises SchemaError: When the schema is invalid.
        :raises MasterSchemaError: When the master schema is invalid.
    """
    if not isinstance(schema, dict):
        msg = ('The top level of the schema file is a {}, whereas a dict is '
               'expected.'.format(type(schema).__name__))
        raise SchemaError(msg)

    if 'version' in schema:
        version = schema['version']
    else:
        raise SchemaError('A format version is expected in the schema.')

    master_schema_bytes = get_master_schema_(version)
    try:
        master_schema = json.loads(master_schema_bytes.decode('utf-8'))
    except ValueError as e:  # In Python 3 we can be more specific with
                             # json.decoder.JSONDecodeError, but that
                             # doesn't exist in Python 2.
        msg = ('The master schema is not a valid JSON file. The schema cannot '
               'be validated. Please file a bug report.')
        raise_from(MasterSchemaError(msg), e)

    try:
        jsonschema.validate(schema, master_schema)
    except jsonschema.exceptions.ValidationError as e:
        raise_from(SchemaError('The schema is not valid.'), e)
    except jsonschema.exceptions.SchemaError as e:
        msg = ('The master schema is not valid. The schema cannot be '
               'validated. Please file a bug report.')
        raise_from(MasterSchemaError(msg), e)


def schema_from_json_file(schema_file):
    # type: (TextIO) -> Schema
    """ Load a Schema object from a json file.

        :param schema_file: A JSON file containing the schema.
        :raises SchemaError: When the schema is invalid.
        :return: The resulting :class:`Schema` object.
    """
    try:
        schema_dict = json.load(schema_file)
    except ValueError as e:  # In Python 3 we can be more specific with
                             # json.decoder.JSONDecodeError, but that
                             # doesn't exist in Python 2.
        raise_from(
            SchemaError('The schema is not a valid JSON file.'),
            e)

    return Schema.from_json_dict(schema_dict, validate=True)
