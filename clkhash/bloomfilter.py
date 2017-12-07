#!/usr/bin/env python3

"""
Generate a Bloom filter
"""
import base64
import hmac
import sys
from hashlib import sha1, md5

from bitarray import bitarray


def update_bloom_filter(bloomfilter, ngrams, key_sha1, key_md5, k):
    """
    adds the encodings of the given n-grams to the provided Bloom filter.
    Note that this function modifies the provided Bloom filter in memory and thus has no return value.

    :param bloomfilter: a bitarray describing the Bloom filter to be updated
    :param ngrams: list of n-grams to be hashed and encoded in filter
    :param key_sha1: hmac secret keys for sha1 as bytes
    :param key_md5: hmac secret keys for md5 as bytes
    :param k: number of hash functions to use per element
    """
    l = bloomfilter.length()
    for m in ngrams:
        sha1hm = int(hmac.new(key_sha1, m.encode(), sha1).hexdigest(), 16) % l
        md5hm = int(hmac.new(key_md5, m.encode(), md5).hexdigest(), 16) % l
        for i in range(k):
            gi = (sha1hm + i * md5hm) % l
            bloomfilter[gi] = 1


def crypto_bloom_filter(record, tokenizers, keys1, keys2, l=1024, k=30):
    """
    Make a bloom filter from a record with given tokenizers and lists of keys.

    Using the method from
    http://www.record-linkage.de/-download=wp-grlc-2011-02.pdf

    :param record: plaintext record tuple. E.g. (index, name, dob, gender)
    :param tokenizers: A list of IdentifierType tokenizers (one for each record element)
    :param keys1: list of keys for first hash function as list of bytes
    :param keys2: list of keys for second hash function as list of bytes

    :return: 3-tuple - bitarray with bloom filter for record, index of record, bitcount
    """
    bloomfilter = bitarray(l)
    bloomfilter.setall(False)

    for (entry, tokenizer, key1, key2) in zip(record, tokenizers, keys1, keys2):
        ngrams = [ngram for ngram in tokenizer(entry)]
        update_bloom_filter(bloomfilter, ngrams, key1, key2, k)

    return bloomfilter, record[0], bloomfilter.count()


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
