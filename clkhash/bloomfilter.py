#!/usr/bin/env python3

"""
Generate a Bloom filter
"""
import base64
import hmac
import sys
from hashlib import sha1, md5

from bitarray import bitarray


def hbloom(mlist, keys_sha1, keys_md5, l=1024, k=30):
    """
    Cryptographic bloom filter for list of strings

    :param mlist: list of strings to be hashed and encoded in filter
    :param keys_sha1: list of hmac secret keys for sha1, one for each element in mList
    :param keys_md5: list of hmac secret keys for md5, one for each element in mList
    :param l: length of filter
    :param k: number of hash functions to use per element
    :return: bitarray with bloom filter
    """
    bf = bitarray(l)
    bf[:] = 0
    for m, key_sha, key_md5 in zip(mlist, keys_sha1, keys_md5):
        sha1hm = int(hmac.new(key_sha, m.encode(), sha1).hexdigest(), 16) % l
        md5hm = int(hmac.new(key_md5, m.encode(), md5).hexdigest(), 16) % l
        for i in range(k):
            gi = (sha1hm + i * md5hm) % l
            bf[gi] = 1
    return bf


def crypto_bloom_filter(record, tokenizers, keys1, keys2):
    """
    Make a bloom filter from a record with given tokenizers

    Using the method from
    http://www.record-linkage.de/-download=wp-grlc-2011-02.pdf

    :param record: plaintext record tuple. E.g. (index, name, dob, gender)
    :param tokenizers: A list of IdentifierType tokenizers (one for each record element)
    :param keys1: list of keys for first hash function as list of bytes
    :param keys2: list of keys for second hash function as list of bytes

    :return: 3-tuple - bitarray with bloom filter for record, index of record, bitcount
    """

    mlist = []
    for (entry, tokenizer) in zip(record, tokenizers):
        for token in tokenizer(entry):
            mlist.append(token)

    bf = hbloom(mlist, keys_sha1=keys1, keys_md5=keys2)

    return bf, record[0], bf.count()


def stream_bloom_filters(dataset, schema_types, keys):
    """
    Yield bloom filters

    :param dataset: An iterable of indexable records.
    :param schema: An iterable of identifier type names.
    :param keys: A tuple of two lists of secret keys used in the HMAC.
    :return: Yields bloom filters as 3-tuples
    """
    for s in dataset:
        yield crypto_bloom_filter(s, schema_types, keys1=keys[0], keys2=keys[1])


def calculate_bloom_filters(dataset, schema, keys):
    """
    :param dataset: A list of indexable records.
    :param schema: An iterable of identifier types.
    :param keys: A tuple of two lists of secret keys used in the HMAC.
    :return: List of bloom filters as 3-tuples, each containing
             bloom filter (bitarray), index (int), bitcount (int)
    """
    return list(stream_bloom_filters(dataset, schema, keys))


def serialize_bitarray(ba):
    """Serialize a bitarray (bloomfilter)

    """

    # Encode bitarray according to the Python version
    if sys.version_info[0] >= 3:
        return base64.encodebytes(ba.tobytes()).decode('utf8')
    else:
        return base64.b64encode(ba.tobytes()).decode('utf8')
