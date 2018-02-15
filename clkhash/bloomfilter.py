#!/usr/bin/env python3

"""
Generate a Bloom filter
"""
import base64
import hashlib
import hmac
import sys
from typing import Callable, Iterable, List, Sequence, Text, Tuple

from bitarray import bitarray
from future.builtins import map

from clkhash import field_formats, tokenizer
from clkhash.backports import int_from_bytes
import clkhash.schema


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
    :param encoding: the encoding to use when turning the ngrams to bytes

    :return: bitarray of length l with the bits set which correspond to the encoding of the ngrams
    """
    bf = bitarray(l)
    bf.setall(False)
    for m in ngrams:
        m_bytes = m.encode(encoding=encoding)

        sha1hm_bytes = hmac.new(key_sha1, m_bytes, hashlib.sha1).digest()
        md5hm_bytes = hmac.new(key_md5, m_bytes, hashlib.md5).digest()

        sha1hm = int_from_bytes(sha1hm_bytes, 'big') % l
        md5hm = int_from_bytes(md5hm_bytes, 'big') % l

        for i in range(k):
            gi = (sha1hm + i * md5hm) % l
            bf[gi] = True
    return bf


def fold_xor(bloomfilter,  # type: bitarray
             folds         # type: int
             ):
    # type: (...) -> bitarray
    """ Performs XOR folding on a Bloom filter.

        If the length of the original Bloom filter is n and we perform
        r folds, then the length of the resulting filter is n / 2 ** r.

        :param bloomfilter: Bloom filter to fold
        :param folds: number of folds

        :return: folded bloom filter
    """

    if len(bloomfilter) % 2 ** folds != 0:
        msg = ('The length of the bloom filter is {length}. It is not '
               'divisible by 2 ** {folds}, so it cannot be folded {folds} '
               'times.'
               .format(length=len(bloomfilter), folds=folds))
        raise ValueError(msg)

    for _ in range(folds):
        bf1 = bloomfilter[:len(bloomfilter) // 2]
        bf2 = bloomfilter[len(bloomfilter) // 2:]

        bloomfilter = bf1 ^ bf2

    return bloomfilter

def crypto_bloom_filter(record,          # type: Sequence[Text]
                        tokenizers,      # type: List[Callable[[Text], Iterable[Text]]]
                        field_hashing,   # type: List[field_formats.FieldHashingProperties]
                        keys,            # type: Tuple[Sequence[bytes], Sequence[bytes]]
                        hash_properties  # type: clkhash.schema.GlobalHashingProperties
                        ):
    # type: (...) -> Tuple[bitarray, Text, int]
    """
    Makes a Bloom filter from a record with given tokenizers and lists of keys.

    Using the method from
    http://www.record-linkage.de/-download=wp-grlc-2011-02.pdf

    :param record: plaintext record tuple. E.g. (index, name, dob, gender)
    :param tokenizers: A tokenizers. A tokenizer is a function that
        returns tokens from a string.
    :param field_hashing: Hashing properties for each field.
    :param keys: Keys for the hash functions as a tuple of lists of bytes.
    :param hash_properties: Global hashing properties.

    :return: 3-tuple:
            - bloom filter for record as a bitarray
            - first element of record (usually an index)
            - number of bits set in the bloomfilter
    """
    keys1, keys2 = keys
    l = hash_properties.l
    k = hash_properties.k
    xor_folds = hash_properties.xor_folds

    bloomfilter = bitarray(l)
    bloomfilter.setall(False)

    for (entry, tokenizer, field, key1, key2) \
            in zip(record, tokenizers, field_hashing, keys1, keys2):
        ngrams = tokenizer(entry)
        adjusted_k = int(round(field.weight * k))

        bloomfilter |= double_hash_encode_ngrams(
            ngrams, key1, key2, adjusted_k, l, field.encoding)

    bloomfilter = fold_xor(bloomfilter, xor_folds)

    return bloomfilter, record[0], bloomfilter.count()


def stream_bloom_filters(dataset,  # type: Iterable[Sequence[Text]]
                         keys,     # type: Tuple[Sequence[bytes], Sequence[bytes]]
                         schema    # type: clkhash.schema.Schema
                         ):
    # type: (...) -> Iterable[Tuple[bitarray, Text, int]]
    """
    Yield bloom filters

    :param dataset: An iterable of indexable records.
    :param schema_types: An iterable of identifier type names.
    :param keys: A tuple of two lists of secret keys used in the HMAC.
    :param xor_folds: number of XOR folds to perform
    :return: Yields bloom filters as 3-tuples
    """
    tokenizers = [tokenizer.get_tokenizer(field.hashing_properties)
                  for field in schema.fields]
    field_hashing = [field.hashing_properties for field in schema.fields]
    hash_properties = schema.hashing_globals

    return (crypto_bloom_filter(s, tokenizers, field_hashing,
                                keys, hash_properties)
            for s in dataset)


def serialize_bitarray(ba):
    # type: (bitarray) -> str
    """Serialize a bitarray (bloomfilter)

    """
    return base64.b64encode(ba.tobytes()).decode('utf8')
