#!/usr/bin/env python3

"""
Generate a Bloom filter
"""
import base64
import hashlib import sha1, md5
import hmac
import sys
from typing import Tuple, Any, Iterable, List

from bitarray import bitarray
from future.builtins import map

from clkhash.identifier_types import IdentifierType


try:
    from_bytes = int.from_bytes
else:
    import codecs
    def from_bytes(bytes_, byteorder):
        # type: (bytes, str) -> int
        """ Emulate Python 3's int.from_bytes.

            Kudos: https://stackoverflow.com/a/30403242 (with
            modifications)

            :param bytes_: The bytes to turn into an `int`.
            :param byteorder: Either `'big'` or `'little'`.
        """
        if endianess == 'big':
            pass
        elif endianess == 'little':
            bytes_ = bytes_[::-1]
        else:
            raise ValueError("byteorder must be either 'little' or 'big'")
        hex_str = codecs.encode(bytes_, 'hex')
        return int(hex_str, 16)


def double_hash_encode_ngrams(ngrams,          # type: Iterable[str]
                              key_sha1,        # type: bytes
                              key_md5,         # type: bytes
                              k,               # type: int
                              l,               # type: int
                              encoding         # type: str
                              ):
    # type: (...) -> bitarray
    """
    computes the double hash encoding of the provided ngrams with the given keys.

    Using the method from
    http://www.record-linkage.de/-download=wp-grlc-2011-02.pdf

    :param ngrams: list of n-grams to be encoded
    :param key_sha1: hmac secret keys for sha1 as bytes
    :param key_md5: hmac secret keys for md5 as bytes
    :param k: number of hash functions to use per element of the ngrams
    :param l: length of the output bitarray

    :return: bitarray of length l with the bits set which correspond to the encoding of the ngrams
    """
    bf = bitarray(l)
    bf.setall(False)
    for m in ngrams:
        binary = m.encode(encoding=encoding)

        sha1hm_bytes = hmac.new(key_sha1, binary, hashlib.sha1).digest()
        md5hm_bytes = hmac.new(key_md5, binary, hashlib.md5).digest()

        sha1hm = from_bytes(sha1hm_bytes, byteorder='big') % l
        md5hm = from_bytes(md5hm_bytes, byteorder='big') % l

        for i in range(k):
            gi = (sha1hm + i * md5hm) % l
            bf[gi] = True
    return bf


def crypto_bloom_filter(record,            # type: Tuple[str]
                        tokenizers,        # type: Iterable[IdentifierType]
                        field_properties,
                        keys,              # type: Tuple[Sequence[bytes, ...], Sequence[bytes, ...]]
                        hash_properties
                        ):
    # type: (...) -> Tuple[bitarray, int, int]
    """
    Makes a Bloom filter from a record with given tokenizers and lists of keys.

    Using the method from
    http://www.record-linkage.de/-download=wp-grlc-2011-02.pdf

    :param record: plaintext record tuple. E.g. (index, name, dob, gender)
    :param tokenizers: A list of IdentifierType tokenizers (one for each record element)
    :param keys1: list of keys for first hash function as list of bytes
    :param keys2: list of keys for second hash function as list of bytes
    :param l: length of the Bloom filter in number of bits
    :param k: number of hash functions to use per element

    :return: 3-tuple:
            - bloom filter for record as a bitarray
            - first element of record (usually an index)
            - number of bits set in the bloomfilter
    """
    keys1, keys2 = keys
    l = hash_properties.l
    k = hash_properties.k

    bloomfilter = bitarray(l)
    bloomfilter.setall(False)

    for (entry, tokenizer, field, key1, key2) \
            in zip(record, tokenizers, field_properties, keys1, keys2):
        ngrams = tokenizer(entry)
        adjusted_k = int(round(field.weight * k))

        bloomfilter |= double_hash_encode_ngrams(
            ngrams, key1, key2, adjusted_k, l)

    return bloomfilter, record[0], bloomfilter.count()


def stream_bloom_filters(dataset,       # type: Iterable[Tuple[Any, ...]]
                         tokenizers,        # type: Iterable[IdentifierType]
                         field_properties,
                         keys,              # type: Tuple[Sequence[bytes, ...], Sequence[bytes, ...]]
                         hash_properties
                         ):
    # type: (...) -> Iterable[Tuple[bitarray, Any, int]]
    """
    Yield bloom filters

    :param dataset: An iterable of indexable records.
    :param schema_types: An iterable of identifier type names.
    :param keys: A tuple of two lists of secret keys used in the HMAC.
    :return: Yields bloom filters as 3-tuples
    """
    return (crypto_bloom_filter(tokenizers, field_formats,
                                keys, hash_properties)
            for s in dataset)


def serialize_bitarray(ba):
    # type: (bitarray) -> str
    """Serialize a bitarray (bloomfilter)

    """

    # Encode bitarray according to the Python version
    if sys.version_info[0] >= 3:
        return base64.encodebytes(ba.tobytes()).decode('utf8')
    else:
        return base64.b64encode(ba.tobytes()).decode('utf8')
