from typing import Tuple, Union, Optional, Sequence

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

"""
We use the block-size of SHA1 and MD5 as the default key size for HMAC
"""
DEFAULT_KEY_SIZE = 64

DEFAULT_NUM_HASHING_METHODS = 2

_HASH_FUNCTIONS = {
    'SHA256': hashes.SHA256,
    'SHA512': hashes.SHA512
}


def hkdf(secret: bytes,
         num_keys: int,
         hash_algo: str = 'SHA256',
         salt: Optional[bytes] = None,
         info: Optional[bytes] = None,
         key_size: int = DEFAULT_KEY_SIZE
         ) -> Tuple[bytes, ...]:
    """
    Executes the HKDF key derivation function as described in rfc5869 to
    derive `num_keys` keys of size `key_size` from the secret.

    :param secret: input keying material
    :param num_keys: the number of keys the kdf should produce
    :param hash_algo: The hash function used by HKDF for the internal
        HMAC calls. The choice of hash function defines the maximum
        length of the output key material. Output bytes <= 255 * hash
        digest size (in bytes).
    :param salt: HKDF is defined to operate with and without random
        salt. This is done to accommodate applications where a salt
        value is not available. We stress, however, that the use of salt
        adds significantly to the strength of HKDF, ensuring
        independence between different uses of the hash function,
        supporting "source-independent" extraction, and strengthening
        the analytical results that back the HKDF design.
        Random salt differs fundamentally from the initial keying
        material in two ways: it is non-secret and can be re-used.
        Ideally, the salt value is a random (or pseudorandom) string
        of the length HashLen.  Yet, even a salt value of less quality
        (shorter in size or with limited entropy) may still make a
        significant contribution to the security of the output keying
        material.
    :param info: While the 'info' value is optional in the definition of
        HKDF, it is often of great importance in applications. Its main
        objective is to bind the derived key material to application-
        and context-specific information. For example, 'info' may
        contain a protocol number, algorithm identifiers, user
        identities, etc.  In particular, it may prevent the derivation
        of the same keying material for different contexts (when the
        same input key material (IKM) is used in such different
        contexts).  It may also accommodate additional inputs to the key
        expansion part, if so desired (e.g., an application may want to
        bind the key material to its length L, thus making L part of the
        'info' field).  There is one technical requirement from 'info':
        it should be independent of the input key material value IKM.
    :param key_size: the size of the produced keys
    :return: Derived keys
    """
    try:
        hash_function = _HASH_FUNCTIONS[hash_algo]
    except KeyError as e:
        msg = f"unsupported hash function '{hash_algo}'"
        raise ValueError(msg) from e

    hkdf = HKDF(algorithm=hash_function(),
                length=num_keys * key_size,
                salt=salt,
                info=info,
                backend=default_backend())
    # hkdf.derive returns a block of num_keys * key_size bytes which we
    # divide up into num_keys chunks, each of size key_size
    keybytes = hkdf.derive(secret)
    keys = tuple(keybytes[i * key_size:(i + 1) * key_size] for i in range(num_keys))
    return keys


def generate_key_lists(secret: Union[bytes, str],
                       num_identifier: int,
                       num_hashing_methods: int = DEFAULT_NUM_HASHING_METHODS,
                       key_size: int = DEFAULT_KEY_SIZE,
                       salt: Optional[bytes] = None,
                       info: Optional[bytes] = None,
                       kdf: str = 'HKDF',
                       hash_algo: str = 'SHA256'
                       ) -> Tuple[Tuple[bytes, ...], ...]:
    """
    Generates `num_hashing_methods` derived keys for each identifier for the secret using a key derivation
    function (KDF).

    The only supported key derivation function for now is 'HKDF'.

    The previous secret usage can be reproduced by setting kdf to 'legacy', but it will use the secret twice.
    This is highly discouraged, as this strategy will map the same n-grams in different identifier
    to the same bits in the Bloom filter and thus does not lead to good results.

    :param secret: a secret (either as bytes or string)
    :param num_identifier: the number of identifiers
    :param num_hashing_methods: number of hashing methods used per identifier, each of them requiring a different key
    :param key_size: the size of the derived keys
    :param salt: salt for the KDF as bytes
    :param info: optional context and application specific information as bytes
    :param kdf: the key derivation function algorithm to use
    :param hash_algo: the hashing algorithm to use (ignored if `kdf` is not 'HKDF')
    :return: The derived keys.
             First dimension is of size num_identifier, second dimension is of size num_hashing_methods
             A key is represented as bytes.
    """
    if num_hashing_methods < 1:
        raise ValueError('num_hashing_methods: "{}" is not supported, it'
                         ' should be greater than 0.'.format(num_hashing_methods))
    try:
        if isinstance(secret, bytes):
            secret_bytes = secret
        else:
            secret_bytes = secret.encode('UTF-8')
    except AttributeError:
        raise TypeError("provided 'secret' has to be either of type bytes or strings.")
    if kdf == 'HKDF':
        # we first create the good number of keys, and we then pack them in the expected way.
        key_tuples = hkdf(secret_bytes, num_hashing_methods * num_identifier,
                          hash_algo=hash_algo, salt=salt,
                          info=info, key_size=key_size)
        # regroup such that we get a tuple of keys for each identifier
        split_list = [key_tuples[(i*num_hashing_methods):((i+1)*num_hashing_methods)] for i in range(num_identifier)]
        return tuple(split_list)
    if kdf == 'legacy':
        return tuple(tuple([secret_bytes] * num_hashing_methods) for _ in range(num_identifier))
    raise ValueError(f'kdf: "{kdf}" is not supported.')
