# -*- coding: utf-8 -*-

""" Schema loading and validation.
"""

from __future__ import unicode_literals

import base64
import json
import pkgutil
from typing import Any, Dict, Hashable, Optional, Sequence, Text, TextIO
from copy import deepcopy

import jsonschema
from future.builtins import map

from clkhash.backports import raise_from
from clkhash.field_formats import FieldSpec, spec_from_json_dict
from clkhash.key_derivation import DEFAULT_KEY_SIZE as DEFAULT_KDF_KEY_SIZE

MASTER_SCHEMA_FILE_NAMES = {1: 'v1.json',
                            2: 'v2.json'}  # type: Dict[Hashable, Text]


class SchemaError(Exception):
    """ The user-defined schema is invalid.
    """


class MasterSchemaError(Exception):
    """ Master schema missing? Corrupted? Otherwise surprising? This is
        the exception for you!
    """


class Schema:
    """Linkage Schema which describes how to encode plaintext identifiers.
    """

    def __init__(self,
                 fields,                            # type: Sequence[FieldSpec]
                 l,                                 # type: int
                 xor_folds=0,                       # type: int
                 kdf_type='HKDF',                   # type: str
                 kdf_hash='SHA256',                 # type: str
                 kdf_info=None,                     # type: Optional[bytes]
                 kdf_salt=None,                     # type: Optional[bytes]
                 kdf_key_size=DEFAULT_KDF_KEY_SIZE  # type: int
                 ):
        # type: (...) -> None
        """ Create a Schema.
            :param fields: the features or field definitions
            :param l: The length of the resulting hash in bits. This is the
                length after XOR folding.
            :param xor_folds: The number of XOR folds to perform on the hash.
            :param kdf_type: The key derivation function to use. Currently,
                the only permitted value is 'HKDF'.
            :param kdf_hash: The hash function to use in key derivation. The
                options are 'SHA256' and 'SHA512'.
            :param kdf_info: The info for key derivation. See documentation
                of :ref:`hkdf` for details.
            :param kdf_salt: The salt for key derivation. See documentation
                of :ref:`hkdf` for details.
            :param kdf_key_size: The size of the derived keys in bytes.
        """
        self.fields = fields
        self.l = l
        self.xor_folds = xor_folds

        self.kdf_type = kdf_type
        self.kdf_type = kdf_type
        self.kdf_hash = kdf_hash
        self.kdf_info = kdf_info
        self.kdf_salt = kdf_salt
        self.kdf_key_size = kdf_key_size

    def __repr__(self):
        return "<Schema (v2): {} fields>".format(len(self.fields))


def convert_v1_to_v2(
        dict  # type: Dict[str, Any]
    ):
    # type: (...) -> Dict[str, Any]
    """
    Convert v1 schema dict to v2 schema dict.
    :param dict: v1 schema dict
    :return: v2 schema dict
    """
    version = dict['version']
    if version != 1:
        raise ValueError('Version {} not 1'.format(version))

    clk_config = dict['clkConfig']
    k = clk_config['k']
    clk_hash = clk_config['hash']

    def convert_feature(f):
        if 'ignored' in f:
            return f

        hashing = f['hashing']
        weight = hashing.get('weight', 1.0)

        if weight == 0:
            return {
                'identifier': f['identifier'],
                'ignored': True
            }

        x = deepcopy(f)
        hashing = x['hashing']
        if 'weight' in hashing:
            del hashing['weight']

        hashing['k'] = int(round(weight * k))
        hashing['hash'] = clk_hash
        return x

    result = {
        'version': 2,
        'clkConfig': {
            'l': clk_config['l'],
            'xor_folds': clk_config.get('xor_folds', 0),
            'kdf': clk_config['kdf']
        },
        'features': list(map(convert_feature, dict['features']))
    }
    return result


def from_json_dict(dct, validate=True):
    # type: (Dict[str, Any], bool) -> Schema
    """ Create a Schema for v1 or v2 according to dct

    :param dct: This dictionary must have a `'features'`
            key specifying the columns of the dataset. It must have
            a `'version'` key containing the master schema version
            that this schema conforms to. It must have a `'hash'`
            key with all the globals.
    :param validate: (default True) Raise an exception if the
            schema does not conform to the master schema.
    :return: the Schema
    """
    if validate:
        # This raises iff the schema is invalid.
        validate_schema_dict(dct)

    version = dct['version']
    if version == 1:
        dct = convert_v1_to_v2(dct)
        if validate:
            validate_schema_dict(dct)
    elif version != 2:
        msg = ('Schema version {} is not supported. '
               'Consider updating clkhash.').format(version)
        raise SchemaError(msg)

    clk_config = dct['clkConfig']
    l = clk_config['l']
    xor_folds = clk_config.get('xor_folds', 0)

    kdf = clk_config['kdf']
    kdf_type = kdf['type']
    kdf_hash = kdf.get('hash', 'SHA256')
    kdf_info_string = kdf.get('info')
    kdf_info = (base64.b64decode(kdf_info_string)
                if kdf_info_string is not None
                else None)
    kdf_salt_string = kdf.get('salt')
    kdf_salt = (base64.b64decode(kdf_salt_string)
                if kdf_salt_string is not None
                else None)
    kdf_key_size = kdf.get('keySize', DEFAULT_KDF_KEY_SIZE)

    fields = list(map(spec_from_json_dict, dct['features']))
    return Schema(fields, l, xor_folds,
                  kdf_type, kdf_hash, kdf_info, kdf_salt, kdf_key_size)


def from_json_file(schema_file, validate=True):
    # type: (TextIO, bool) -> Schema
    """ Load a Schema object from a json file.
        :param schema_file: A JSON file containing the schema.
        :param validate: (default True) Raise an exception if the
            schema does not conform to the master schema.
        :raises SchemaError: When the schema is invalid.
        :return: the Schema
    """
    try:
        schema_dict = json.load(schema_file)
    except ValueError as e:  # In Python 3 we can be more specific
        # with json.decoder.JSONDecodeError,
        # but that doesn't exist in Python 2.
        msg = 'The schema is not a valid JSON file.'
        raise_from(SchemaError(msg), e)

    return from_json_dict(schema_dict, validate=validate)


def _get_master_schema(version):
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
        schema_bytes = pkgutil.get_data('clkhash', 'schemas/{}'.format(file_name))
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

    master_schema_bytes = _get_master_schema(version)
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
