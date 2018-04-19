from typing import cast, Tuple, Union, Optional, Sequence, Any

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend
from future.builtins import range, zip


"""
We use the block-size of SHA1 and MD5 as the default key size for HMAC
"""
DEFAULT_KEY_SIZE = 64


class HKDFconfig:
    supported_hash_algos = 'SHA256', 'SHA512'

    def __init__(self,
                 master_secret,   # type: bytes
                 salt=None,             # type: Optional[bytes]
                 info=None,             # type: Optional[bytes]
                 hash_algo='SHA256'     # type: str
                 ):                     # type: (...) -> None
        """
        The parameters for the HDKF are defined as follows:

        master_secret
            input keying material

        salt
            HKDF is defined to operate with and without random salt.  This is
            done to accommodate applications where a salt value is not available.
            We stress, however, that the use of salt adds significantly to the
            strength of HKDF, ensuring independence between different uses of the
            hash function, supporting "source-independent" extraction, and
            strengthening the analytical results that back the HKDF design.

            Random salt differs fundamentally from the initial keying material in
            two ways: it is non-secret and can be re-used.

            Ideally, the salt value is a random (or pseudorandom) string of the
            length HashLen.  Yet, even a salt value of less quality (shorter in
            size or with limited entropy) may still make a significant
            contribution to the security of the output keying material.

        info
            While the 'info' value is optional in the definition of HKDF, it is
            often of great importance in applications.  Its main objective is to
            bind the derived key material to application- and context-specific
            information.  For example, 'info' may contain a protocol number,
            algorithm identifiers, user identities, etc.  In particular, it may
            prevent the derivation of the same keying material for different
            contexts (when the same input key material (IKM) is used in such
            different contexts).  It may also accommodate additional inputs to
            the key expansion part, if so desired (e.g., an application may want
            to bind the key material to its length L, thus making L part of the
            'info' field).  There is one technical requirement from 'info': it
            should be independent of the input key material value IKM.

        hash_algo
            The hash function used by HKDF for the internal HMAC calls. The
            choice of hash function defines the maximum length of the output
            key material. Output bytes <= 255 * hash digest size (in bytes).


        :param master_secret: the input keying material for the kdf as bytes
        :param salt: optional salt value (a non-secret random value) as bytes
        :param info: optional context and application specific information (can be a zero-length string) as bytes
        :param hash_algo: the type of hash function to be used. Either 'SHA256' or 'SHA512'.
        """
        self.master_secret = self.check_is_bytes(master_secret)
        self.info = self.check_is_bytes_or_none(info)
        self.salt = self.check_is_bytes_or_none(salt)
        if hash_algo in HKDFconfig.supported_hash_algos:
            self.hash_algo = hash_algo
        else:
            raise ValueError('hash algorithm "{}" is not supported. Has to be one of {}'.format(hash_algo,
                                                                                                HKDFconfig.supported_hash_algos))

    @staticmethod
    def check_is_bytes(value):
        # type: (Any) -> bytes
        if isinstance(value, bytes):
            return value
        else:
            raise TypeError('provided value is not of type "bytes"')

    @staticmethod
    def check_is_bytes_or_none(value):
        # type: (Any) -> Optional[bytes]
        if value is None:
            return value
        else:
            return HKDFconfig.check_is_bytes(value)


def hkdf(hkdf_config, num_keys, key_size=DEFAULT_KEY_SIZE):
    # type: (HKDFconfig, int, int) -> Tuple[bytes, ...]
    """
    Executes the HKDF key derivation function as described in rfc5869 to derive
    `num_keys` keys of size `key_size` from the master_secret.

    :param hkdf_config: an HKDFconfig object containing the configuration for the HKDF.
    :param num_keys: the number of keys the kdf should produce
    :param key_size: the size of the produced keys
    :return: Derived keys
    """
    hash_dict = {
        'SHA256': hashes.SHA256,
        'SHA512': hashes.SHA512
    }
    if not isinstance(hkdf_config, HKDFconfig):
        raise TypeError('provided config has to be of type "HKDFconfig"')
    hkdf = HKDF(algorithm=hash_dict[hkdf_config.hash_algo](), length=num_keys * key_size, salt=hkdf_config.salt,
                info=hkdf_config.info, backend=default_backend())
    # hkdf.derive returns a block of num_keys * key_size bytes which we divide up into num_keys chunks,
    # each of size key_size
    keybytes = hkdf.derive(hkdf_config.master_secret)
    keys = tuple(keybytes[i * key_size:(i + 1) * key_size] for i in range(num_keys))
    return keys


def generate_key_lists(master_secrets,              # type: Sequence[Union[bytes, str]]
                       num_identifier,              # type: int
                       key_size=DEFAULT_KEY_SIZE,   # type: int
                       salt=None,                   # type: Optional[bytes]
                       info=None,                   # type: Optional[bytes]
                       kdf='HKDF',                  # type: str
                       hash_algo='SHA256'           # type: str
                       ):
    # type: (...) -> Tuple[Tuple[bytes, ...], ...]
    """
    Generates a derived key for each identifier for each master secret using a key derivation function (KDF).

    The only supported key derivation function for now is 'HKDF'.

    The previous key usage can be reproduced by setting kdf to 'legacy'.
    This is highly discouraged, as this strategy will map the same n-grams in different identifier
    to the same bits in the Bloom filter and thus does not lead to good results.

    :param master_secrets: a list of master secrets (either as bytes or strings)
    :param num_identifier: the number of identifiers
    :param key_size: the size of the derived keys
    :param salt: salt for the KDF as bytes
    :param info: optional context and application specific information as bytes
    :param kdf: the key derivation function algorithm to use
    :param hash_algo: the hashing algorithm to use (ignored if `kdf` is not 'HKDF')
    :return: The derived keys.
             First dimension is of size num_identifier, second dimension is the same as master_secrets.
             A key is represented as bytes.
    """
    keys = []
    try:
        for key in master_secrets:
            if isinstance(key, bytes):
                keys.append(key)
            else:
                keys.append(key.encode('UTF-8'))
    except AttributeError:
        raise TypeError("provided 'master_secrets' have to be either of type bytes or strings.")
    if kdf == 'HKDF':
        key_lists = [hkdf(HKDFconfig(key, salt=salt, info=info,
                                     hash_algo=hash_algo),
                          num_identifier,
                          key_size)
                     for key in keys]
        # regroup such that we get a tuple of keys for each identifier
        return tuple(zip(*key_lists))
    if kdf == 'legacy':
        return tuple(tuple(keys) for _ in range(num_identifier))
    raise ValueError('kdf: "{}" is not supported.'.format(kdf))
