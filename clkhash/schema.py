""" Schema loading and validation.
"""
import base64
import json
import pkgutil
from typing import Any, Dict, Hashable, Optional, Sequence, Text, TextIO
from copy import deepcopy

import jsonschema

from clkhash.field_formats import FieldSpec, spec_from_json_dict, InvalidSchemaError
from clkhash.key_derivation import DEFAULT_KEY_SIZE as DEFAULT_KDF_KEY_SIZE

MASTER_SCHEMA_FILE_NAMES = {1: 'v1.json',
                            2: 'v2.json',
                            3: 'v3.json'}  # type: Dict[Hashable, Text]


class SchemaError(Exception):
    """ The user-defined schema is invalid.
    """

    def __init__(self,
                 msg: str,
                 errors: Optional[Sequence[InvalidSchemaError]] = None
                 ) -> None:
        self.msg = msg
        self.errors = [] if errors is None else errors
        super().__init__(msg)

    def __str__(self) -> str:
        detail = ""
        for i, e in enumerate(self.errors, start=1):
            detail += f"Error {i} in feature at index {e.field_spec_index} - {str(e)}\n"
            detail += f"Invalid spec:\n{e.json_field_spec}\n---\n"

        return self.msg + '\n\n' + detail


class MasterSchemaError(Exception):
    """ Master schema missing? Corrupted? Otherwise surprising? This is
        the exception for you!
    """


class Schema:
    """Linkage Schema which describes how to encode plaintext identifiers.

    :ivar fields: the features or field definitions
    :ivar int l: The length of the resulting encoding in bits. This is the length after XOR folding.
    :ivar int xor_folds: The number of XOR folds to perform on the hash.
    :ivar str kdf_type: The key derivation function to use. Currently,
        the only permitted value is 'HKDF'.
    :ivar str kdf_hash: The hash function to use in key derivation. The
        options are 'SHA256' and 'SHA512'.
    :ivar bytes kdf_info: The info for key derivation. See documentation
        of :func:`key_derivation.hkdf` for details.
    :ivar bytes kdf_salt: The salt for key derivation. See documentation
        of :func:`key_derivation.hkdf` for details.
    :ivar int kdf_key_size: The size of the derived keys in bytes.
    """

    def __init__(self,
                 fields: Sequence[FieldSpec],
                 l: int,
                 xor_folds: int = 0,
                 kdf_type: str = 'HKDF',
                 kdf_hash: str = 'SHA256',
                 kdf_info: Optional[bytes] = None,
                 kdf_salt: Optional[bytes] = None,
                 kdf_key_size: int = DEFAULT_KDF_KEY_SIZE
                 ) -> None:
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
        return f"<Schema (v3): {len(self.fields)} fields>"


def _convert_v1_to_v2(schema_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert v1 schema dict to v2 schema dict.
    :param schema_dict: v1 schema dict
    :return: v2 schema dict
    """
    schema_dict = deepcopy(schema_dict)
    version = schema_dict['version']
    if version != 1:
        raise ValueError(f'Version {version} not 1')

    clk_config = schema_dict['clkConfig']
    k = clk_config.pop('k')
    clk_hash = clk_config['hash']

    def convert_feature(f):
        if f.get('ignored', False):
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

        hashing['strategy'] = {}
        hashing['strategy']['k'] = int(round(weight * k))
        hashing['hash'] = clk_hash
        return x

    result = {
        'version': 2,
        'clkConfig': {
            'l': clk_config['l'],
            'xor_folds': clk_config.get('xor_folds', 0),
            'kdf': clk_config['kdf']
        },
        'features': list(map(convert_feature, schema_dict['features']))
    }
    return result


def _convert_v2_to_v3(schema_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert v2 schema dict to v3 schema dict.
    :param schema_dict: v2 schema dict
    :return: v3 schema dict
    """
    schema_dict = deepcopy(schema_dict)
    version = schema_dict['version']
    if version != 2:
        raise ValueError(f'Version {version} not 2')
    schema_dict['version'] = 3
    for feature in schema_dict['features']:
        if feature.get('ignored', False):
            continue
        strategy = feature['hashing']['strategy']
        if 'k' in strategy:
            strategy['bitsPerToken'] = strategy.pop('k')
        elif 'numBits' in strategy:
            strategy['bitsPerFeature'] = strategy.pop('numBits')
        ngrams = feature['hashing']['ngram']
        feature['hashing']['comparison'] = {'type': 'ngram', 'n': feature['hashing'].pop('ngram'), 'positional': feature['hashing'].pop('positional', False)}
    return schema_dict


def convert_to_latest_version(schema_dict: Dict[str, Any], validate_result: Optional[bool] = False) -> Dict[str, Any]:
    """ Convert the given schema to latest schema version.

     :param schema_dict: A dictionary describing a linkage schema. This dictionary must have a `'version'` key
            containing a master schema version. The rest of the schema dict must conform to the corresponding
            master schema.
     :param validate_result: validate converted schema against schema specification
     :return: schema dict of the latest version
     :raises SchemaError: if schema version is not supported
     """
    version = schema_dict.get('version', "'not specified'")
    if version not in MASTER_SCHEMA_FILE_NAMES.keys():
        msg = ('Schema version {} is not supported. '
               'Consider updating clkhash.').format(version)
        raise SchemaError(msg)
    if schema_dict['version'] == 1:
        schema_dict = _convert_v1_to_v2(schema_dict)
    if schema_dict['version'] == 2:
        schema_dict = _convert_v2_to_v3(schema_dict)
    if validate_result:
        validate_schema_dict(schema_dict)
    return schema_dict


def from_json_dict(dct: Dict[str, Any], validate: bool = True) -> Schema:
    """ Create a Schema of the most recent version according to dct

    if the provided schema dict is of an older version, then it will be automatically converted to the latest.

    :param dct: This dictionary must have a `'features'`
            key specifying the columns of the dataset. It must have
            a `'version'` key containing the master schema version
            that this schema conforms to. It must have a `'hash'`
            key with all the globals.
    :param validate: (default True) Raise an exception if the
            schema does not conform to the master schema.
    :raises SchemaError: An exception containing details about why
            the schema is not valid.
    :return: the Schema
    """
    if validate:
        # This raises iff the schema is invalid.
        validate_schema_dict(dct)
    dct = convert_to_latest_version(dct)
    if validate:
        validate_schema_dict(dct)
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

    # Try to parse each feature config and store any errors encountered
    # for reporting.
    feature_errors = []
    feature_configs = []

    for i, feature_config in enumerate(dct['features']):
        try:
            feature_configs.append(spec_from_json_dict(feature_config))
        except InvalidSchemaError as e:
            e.field_spec_index = i
            e.json_field_spec = feature_config
            feature_errors.append(e)

    if len(feature_errors):
        raise SchemaError("Schema was invalid", feature_errors)

    return Schema(feature_configs, l, xor_folds,
                  kdf_type, kdf_hash, kdf_info, kdf_salt, kdf_key_size)


def from_json_file(schema_file: TextIO, validate: bool = True) -> Schema:
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
        raise SchemaError(msg) from e

    return from_json_dict(schema_dict, validate=validate)


def _get_master_schema(version: Hashable) -> dict:
    """ Loads the master schema of given version

        :param version: The version of the master schema whose path we
            wish to retrieve.
        :raises SchemaError: When the schema version is unknown. This
            usually means that either (a) clkhash is out of date, or (b)
            the schema version listed is incorrect.
        :raises MasterSchemaError: When the master schema is invalid.
        :return: Dict object of the (json) master schema.
    """
    try:
        file_name = MASTER_SCHEMA_FILE_NAMES[version]
    except (TypeError, KeyError) as e:
        msg = ('Schema version {} is not supported. '
               'Consider updating clkhash.').format(version)
        raise SchemaError(msg) from e

    try:
        schema_bytes = pkgutil.get_data('clkhash', f'schemas/{file_name}')
        if schema_bytes is None:
            msg = ('The master schema could not be loaded. The schema cannot be '
                   'validated. Please file a bug report.')
            raise MasterSchemaError(msg)
    except FileNotFoundError as e:
        msg = ('The master schema could not be found. The schema cannot be '
               'validated. Please file a bug report.')
        raise MasterSchemaError(msg) from e

    try:
        master_schema = json.loads(schema_bytes.decode('utf-8'))
        return master_schema
    except json.decoder.JSONDecodeError as e:
        msg = ('The master schema is not a valid JSON file. The schema cannot '
               'be validated. Please file a bug report.')
        raise MasterSchemaError(msg) from e


def validate_schema_dict(schema: Dict[str, Any]) -> None:
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

    master_schema = _get_master_schema(version)

    try:
        jsonschema.validate(schema, master_schema)
    except jsonschema.exceptions.ValidationError as e:
        raise SchemaError('The schema is not valid.\n\n' + str(e)) from e
    except jsonschema.exceptions.SchemaError as e:
        msg = ('The master schema is not valid. The schema cannot be '
               'validated. Please file a bug report.')
        raise MasterSchemaError(msg) from e
