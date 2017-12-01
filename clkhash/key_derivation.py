from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend


"""
We use the block-size of SHA1 or MD5 as the default key size for HMAC
"""
DEFAULT_KEY_SIZE = 64


def hkdf(master_secret, num_keys, key_size=DEFAULT_KEY_SIZE, salt=None, info=None):
    """
    Executes the HKDF key derivation function as described in rfc5869 to derive `num_keys` keys from the master_secret.

    :param master_secret: the source of entropy for the kdf
    :param num_keys: the number of keys the kdf should produce
    :param key_size: the size of the produces keys
    :param salt: the salt for the kdf as bytestring.
    :param info: optional context and application specific information
    :return: a list of keys as a list of bytestrings.
    """
    hkdf = HKDF(algorithm=hashes.SHA256(), length=num_keys * key_size, salt=salt, info=info, backend=default_backend())
    keybytes = hkdf.derive(master_secret)
    keys = [keybytes[i * key_size:(i + 1) * key_size] for i in range(num_keys)]
    return keys


def generate_key_lists(master_secrets, num_identifier, key_size=DEFAULT_KEY_SIZE, salt=None, info=None, algo='HKDF'):
    """
    Generates a derived key for each identifier for each master secret.

    The only supported algo parameter for now is 'HKDF'. You can also set it to 'legacy' to reproduce the previous key
    usage, but this is highly discouraged, as this strategy is a) not consistent with the paper, and b) does not lead to
    good results.

    :param master_secrets: a list of master secrets (either as bytes or strings)
    :param num_identifier: the number of identifier
    :param key_size: the size of the derived keys
    :param salt: salt for the KDF
    :param info: optional context and application specific information
    :param algo: the algorithm to derive the keys
    :reb = bturn: a list of lists of keys. First dimension is the same as master_secrets, second dimension is of size
    num_identifer. A key is represented as a bytestring.
    """
    keys = []
    try:
        for key in master_secrets:
            if isinstance(key, bytes):
                keys.append(key)
            else:
                keys.append(key.encode('UTF-8'))
    except SyntaxError:
        raise ValueError("provided 'master_secrets' have to be either of type bytes or strings.")
    if algo is 'HKDF':
        return [hkdf(key, num_identifier, key_size, salt, info) for key in keys]
    if algo is 'legacy':
        return [[key] * num_identifier for key in keys]
    raise ValueError('algo: "{}" is not supported.'.format(algo))
