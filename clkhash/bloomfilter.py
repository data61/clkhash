#!/usr/bin/env python3

"""
Generate a Bloom filter
"""
from typing import Tuple, Any, Iterable, List

import base64
import hmac
import math
import struct
import sys

from clkhash.identifier_types import IdentifierType
from hashlib import sha1, md5
try:
    from hashlib import blake2b
except ImportError:
    from pyblake2 import blake2b

from bitarray import bitarray


def double_hash_encode_ngrams(ngrams,          # type: Iterable[str]
                              key_sha1,        # type: bytes
                              key_md5,         # type: bytes
                              k,               # type: int
                              l                # type: int
                              ):
    # type: (...) -> bitarray.bitarray
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
        sha1hm = int(hmac.new(key_sha1, m.encode(), sha1).hexdigest(), 16) % l
        md5hm = int(hmac.new(key_md5, m.encode(), md5).hexdigest(), 16) % l
        for i in range(k):
            gi = (sha1hm + i * md5hm) % l
            bf[gi] = 1
    return bf


def blake_encode_ngrams(ngrams,          # type: Iterable[str]
                       key,              # type: bytes
                       k,                # type: int
                       l                 # type: int
                       ):
    # type: (...) -> bitarray.bitarray
    """
    computes the encoding of the provided ngrams using the BLAKE2 hash function keyed with the given key.

    We deliberately do not use the double hashing scheme as proposed in
    http://www.record-linkage.de/-download=wp-grlc-2011-02.pdf, because this would introduce an exploitable structure
    into the Bloom filter. For more details on the weakness, see [Kroll2015]_.
    In short, the double hashing scheme only allows for :math:`l^2` different encodings for any possible n-gram,
    whereas the use of :math:`k` different independent hash functions gives you :math:`\sum_{j=1}^k{\binom{l}{j}}`
    combinations.

    Our construction
    ----------------
    It is advantageous to construct Bloom filters using a family of hash functions with the property of
    `k-independence <https://en.wikipedia.org/wiki/K-independent_hashing>`_ to compute the indices for an entry.
    This approach minimises the change of collisions.

    An informal definition of *k-independence* of a family of hash functions is, that if selecting a function at random
    from the family, it guarantees that the hash codes of any designated k keys are independent random variables.

    Our construction utilises the fact that the output bits of a cryptographic hash function are uniformly distributed,
    independent, binary random variables (well, at least as close to as possible. See [Kaminsky2011]_ for an analysis).
    Thus, slicing the output of a cryptographic hash function into k different slices gives you k independent random
    variables.


    .. warning::
       Please be aware that, although this construction makes the attack of [Kroll2015]_ infeasible, it is most likely
       not enough to ensure security. Or in their own words:

       However, we think that using independent hash functions alone will not be sufficient to ensure security, since
       in this case other approaches (maybe related to or at least inspired through work from the area of Frequent
       Itemset Mining [19]) are promising to detect at least the most frequent atoms automatically.


    .. [Kroll2015] Kroll, M., & Steinmetzer, S. (2015).
       Who is 1011011111...1110110010? automated cryptanalysis of bloom filter encryptions of databases with several
       personal identifiers.
       In Communications in Computer and Information Science. https://doi.org/10.1007/978-3-319-27707-3_21

    .. [Kaminsky2011] Kaminsky, A. (2011).
       GPU Parallel Statistical and Cube Test Analysis of the SHA-3 Finalist Candidate Hash Functions.
       https://www.cs.rit.edu/~ark/parallelcrypto/sha3test01/jce2011.pdf

    :param ngrams: list of n-grams to be encoded
    :param key: secret key for blake2 as bytes
    :param k: number of hash functions to use per element of the ngrams
    :param l: length of the output bitarray (has to be a power of 2)

    :return: bitarray of length l with the bits set which correspond to the encoding of the ngrams
    """
    log_l = int(math.log(l, 2))
    if not 2**log_l == l:
        raise ValueError('parameter "l" has to be a power of two for the BLAKE2 encoding, but was: {}'.format(l))
    bf = bitarray(l)
    bf.setall(False)
    if k < 1:
        return bf
    num_macs = (k+31) // 32

    for m in ngrams:
        random_shorts = []
        for i in range(num_macs):
            hash_bytes = blake2b(m.encode(), key=key, salt=str(i).encode()).digest()
            random_shorts.extend(struct.unpack('32H', hash_bytes))  # interpret hash bytes as 32 unsigned shorts.
        for i in range(k):
            idx = random_shorts[i] % l
            bf[idx] = 1
    return bf


def crypto_bloom_filter(record,         # type: Tuple[Any, ...]
                        tokenizers,     # type: Iterable[IdentifierType]
                        keys1,          # type: Tuple[bytes, ...]
                        keys2,          # type: Tuple[bytes, ...]
                        l=1024,         # type: int
                        k=30            # type: int
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
    bloomfilter = bitarray(l)
    bloomfilter.setall(False)

    for (entry, tokenizer, key1, key2) in zip(record, tokenizers, keys1, keys2):
        ngrams = [ngram for ngram in tokenizer(str(entry))]
        if tokenizer.weight < 0:
            raise ValueError('weight must not be smaller than zero, but was: {}'.format(tokenizer.weight))
        adjusted_k = int(round(tokenizer.weight * k))
        bloomfilter |= double_hash_encode_ngrams(ngrams, key1, key2, adjusted_k, l)

    return bloomfilter, record[0], bloomfilter.count()


def stream_bloom_filters(dataset,       # type: Iterable[Tuple[Any, ...]]
                         schema_types,  # type: Iterable[IdentifierType]
                         keys           # type: Tuple[Tuple[bytes, ...],Tuple[bytes, ...]]
                         ):
    # type: (...) -> Iterable[Tuple[bitarray, Any, int]]
    """
    Yield bloom filters

    :param dataset: An iterable of indexable records.
    :param schema_types: An iterable of identifier type names.
    :param keys: A tuple of two lists of secret keys used in the HMAC.
    :return: Yields bloom filters as 3-tuples
    """
    for s in dataset:
        yield crypto_bloom_filter(s, schema_types, keys1=keys[0], keys2=keys[1])


def calculate_bloom_filters(dataset,    # type: Iterable[Tuple[Any]]
                            schema,     # type: Iterable[IdentifierType]
                            keys        # type: Tuple[Tuple[bytes], Tuple[bytes]]
                            ):
    # type: (...) -> List[Tuple[bitarray, Any, int]]
    """
    :param dataset: A list of indexable records.
    :param schema: An iterable of identifier types.
    :param keys: A tuple of two lists of secret keys used in the HMAC.
    :return: List of bloom filters as 3-tuples, each containing
             bloom filter (bitarray), record first element - usually index, bitcount (int)
    """
    return list(stream_bloom_filters(dataset, schema, keys))


def serialize_bitarray(ba):
    # type: (bitarray) -> str
    """Serialize a bitarray (bloomfilter)

    """

    # Encode bitarray according to the Python version
    if sys.version_info[0] >= 3:
        return base64.encodebytes(ba.tobytes()).decode('utf8')
    else:
        return base64.b64encode(ba.tobytes()).decode('utf8')
