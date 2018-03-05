#!/usr/bin/env python3

"""
Generate a Bloom filter
"""
from typing import Tuple, Any, Iterable, List

import base64
import hmac
import math
import struct

from future.builtins import range
from enum import Enum
from clkhash.identifier_types import IdentifierType
from functools import partial
from hashlib import sha1, md5

try:
    from hashlib import blake2b
except ImportError:
    from pyblake2 import blake2b  # type: ignore

from bitarray import bitarray


def double_hash_encode_ngrams(ngrams,          # type: Iterable[str]
                              keys,            # type: Tuple[bytes, ...]
                              k,               # type: int
                              l                # type: int
                              ):
    # type: (...) -> bitarray
    """
    Computes the double hash encoding of the provided ngrams with the given keys.

    Using the method from
    http://www.record-linkage.de/-download=wp-grlc-2011-02.pdf

    :param ngrams: list of n-grams to be encoded
    :param keys: hmac secret keys for md5 and sha1 as bytes
    :param k: number of hash functions to use per element of the ngrams
    :param l: length of the output bitarray

    :return: bitarray of length l with the bits set which correspond to the encoding of the ngrams
    """
    key_sha1, key_md5 = keys
    bf = bitarray(l)
    bf.setall(False)
    for m in ngrams:
        sha1hm = int(hmac.new(key_sha1, m.encode(), sha1).hexdigest(), 16) % l
        md5hm = int(hmac.new(key_md5, m.encode(), md5).hexdigest(), 16) % l
        for i in range(k):
            gi = (sha1hm + i * md5hm) % l
            bf[gi] = 1
    return bf


def double_hash_encode_ngrams_non_singular(ngrams,          # type: Iterable[str]
                              keys,            # type: Tuple[bytes, ...]
                              k,               # type: int
                              l                # type: int
                              ):
    # type: (...) -> bitarray.bitarray
    """
    computes the double hash encoding of the provided n-grams with the given keys.

    The original construction of [Schnell2011]_ displays an abnormality for certain inputs:
      An n-gram can be encoded into just one bit irrespective of the number of k.

    Their construction goes as follows: the :math:`k` different indices :math:`g_i` of the Bloom filter for an n-gram
    :math:`x` are defined as:

    .. math::
      g_{i}(x) = (h_1(x) + i h_2(x)) \mod l

    with :math:`0 \leq i < k` and :math:`l` is the length of the Bloom filter. If the value of the hash of :math:`x` of
    the second hash function is a multiple of :math:`l`, then

    .. math::
      h_2(x) = 0 \mod l

    and thus

    .. math::
      g_i(x) = h_1(x) \mod l,

    irrespective of the value :math:`i`. A discussion of this potential flaw can be found
    `here <https://github.com/n1analytics/clkhash/issues/33>`_.

    .. [Schnell2011] Schnell, R., Bachteler, T., & Reiher, J. (2011). A Novel Error-Tolerant Anonymous Linking Code.
       http://soz-159.uni-duisburg.de/wp-content/uploads/2017/05/downloadwp-grlc-2011-02.pdf

    :param ngrams: list of n-grams to be encoded
    :param key_sha1: hmac secret keys for sha1 as bytes
    :param key_md5: hmac secret keys for md5 as bytes
    :param k: number of hash functions to use per element of the ngrams
    :param l: length of the output bitarray

    :return: bitarray of length l with the bits set which correspond to the encoding of the ngrams
    """
    key_sha1, key_md5 = keys
    bf = bitarray(l)
    bf.setall(False)
    for m in ngrams:
        sha1hm = int(hmac.new(key_sha1, m.encode(), sha1).hexdigest(), 16) % l
        md5hm = int(hmac.new(key_md5, m.encode(), md5).hexdigest(), 16) % l
        i = 0
        while md5hm == 0:
            md5hm = int(hmac.new(key_md5, m.encode() + chr(i).encode(), md5).hexdigest(), 16) % l
            i += 1
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
    Computes the encoding of the provided ngrams using the BLAKE2 hash function.

    We deliberately do not use the double hashing scheme as proposed in [Schnell2011]_, because this
    would introduce an exploitable structure into the Bloom filter. For more details on the
    weakness, see [Kroll2015]_.

    In short, the double hashing scheme only allows for :math:`l^2` different encodings for any possible n-gram,
    whereas the use of :math:`k` different independent hash functions gives you :math:`\sum_{j=1}^{k}{\\binom{l}{j}}`
    combinations.


    **Our construction**

    It is advantageous to construct Bloom filters using a family of hash functions with the property of
    `k-independence <https://en.wikipedia.org/wiki/K-independent_hashing>`_ to compute the indices for an entry.
    This approach minimises the change of collisions.

    An informal definition of *k-independence* of a family of hash functions is, that if selecting a function at random
    from the family, it guarantees that the hash codes of any designated k keys are independent random variables.

    Our construction utilises the fact that the output bits of a cryptographic hash function are uniformly distributed,
    independent, binary random variables (well, at least as close to as possible. See [Kaminsky2011]_ for an analysis).
    Thus, slicing the output of a cryptographic hash function into k different slices gives you k independent random
    variables.

    We chose Blake2 as the cryptographic hash function mainly for two reasons:

    * it is fast.
    * in keyed hashing mode, Blake2 provides MACs with just one hash function call instead of the
      two calls in the HMAC construction used in the double hashing scheme.


    .. warning::
       Please be aware that, although this construction makes the attack of [Kroll2015]_ infeasible, it is most likely
       not enough to ensure security. Or in their own words:

         | However, we think that using independent hash functions alone will not be sufficient to ensure security, since
           in this case other approaches (maybe related to or at least inspired through work from the area of Frequent
           Itemset Mining) are promising to detect at least the most frequent atoms automatically.

    .. [Schnell2011] Schnell, R & Bachteler, T, and Reiher, J.
       A Novel Error-Tolerant Anonymous Linking Code
       http://www.record-linkage.de/-download=wp-grlc-2011-02.pdf

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
        random_shorts = []  # type: List[int]
        for i in range(num_macs):
            hash_bytes = blake2b(m.encode(), key=key, salt=str(i).encode()).digest()
            random_shorts.extend(struct.unpack('32H', hash_bytes))  # interpret hash bytes as 32 unsigned shorts.
        for i in range(k):
            idx = random_shorts[i] % l
            bf[idx] = 1
    return bf


class NgramEncodings(Enum):
    """
    Lists the available schemes for encoding n-grams.

    .. note::
      the slightly awkward looking construction with the calls to partial and the overwrite of __call__ are due to
      compatibility issues with Python 2.7.
    """
    DOUBLE_HASH = partial(double_hash_encode_ngrams)
    """ the initial encoding scheme as described in Schnell, R., Bachteler, T., & Reiher, J. (2011). A Novel 
    Error-Tolerant Anonymous Linking Code. Also see :meth:`double_hash_encode_ngrams`"""
    BLAKE_HASH = partial(blake_encode_ngrams)
    """ uses the BLAKE2 hash function, which is one of the fastest modern hash functions, and does less hash function 
    calls compared to the DOUBLE_HASH based schemes. It avoids one of the exploitable weaknesses of the DOUBLE_HASH 
    scheme. Also see :meth:`blake_encode_ngrams`"""
    DOUBLE_HASH_NON_SINGULAR = partial(double_hash_encode_ngrams_non_singular)
    """ very similar to DOUBLE_HASH, but avoids singularities in the encoding. Also see 
    :meth:`double_hash_encode_ngrams_non_singular`"""

    def __call__(self, *args):
        return self.value(*args)


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


def crypto_bloom_filter(record,       # type: Tuple[Any, ...]
                        tokenizers,   # type: Iterable[IdentifierType]
                        keys,         # type: Tuple[Tuple[bytes, ...]]
                        xor_folds=0,  # type: int
                        l=1024,       # type: int
                        k=30,         # type: int
                        ngram_encoding=NgramEncodings.DOUBLE_HASH
                        ):
    # type: (...) -> Tuple[bitarray, int, int]
    """
    Makes a Bloom filter from a record with given tokenizers and lists of keys.

    Using the method from
    http://www.record-linkage.de/-download=wp-grlc-2011-02.pdf

    :param record: plaintext record tuple. E.g. (index, name, dob, gender)
    :param tokenizers: A list of IdentifierType tokenizers (one for each record element)
    :param keys: tuple of tuple of keys for the hash functions as bytes
    :param xor_folds: number of XOR folds to perform
    :param l: length of the Bloom filter in number of bits
    :param k: number of hash functions to use per element
    :param ngram_encoding:

    :return: 3-tuple:
            - bloom filter for record as a bitarray
            - first element of record (usually an index)
            - number of bits set in the bloomfilter
    """
    bloomfilter = bitarray(l)
    bloomfilter.setall(False)

    for (entry, tokenizer, f_keys) in zip(record, tokenizers, keys):
        ngrams = [ngram for ngram in tokenizer(str(entry))]
        if tokenizer.weight < 0:
            raise ValueError('weight must not be smaller than zero, but was: {}'.format(tokenizer.weight))
        adjusted_k = int(round(tokenizer.weight * k))
        bloomfilter |= ngram_encoding(ngrams, f_keys, adjusted_k, l)

    bloomfilter = fold_xor(bloomfilter, xor_folds)

    return bloomfilter, record[0], bloomfilter.count()


def stream_bloom_filters(dataset,       # type: Iterable[Tuple[Any, ...]]
                         schema_types,  # type: Iterable[IdentifierType]
                         keys,          # type: Tuple[Tuple[bytes, ...]]
                         xor_folds=0    # type: int
                         ):
    # type: (...) -> Iterable[Tuple[bitarray, Any, int]]
    """
    Yield bloom filters

    :param dataset: An iterable of indexable records.
    :param schema_types: An iterable of identifier type names.
    :param keys: A tuple of two lists of secret keys used in the HMAC.
    :param xor_folds: number of XOR folds to perform
    :return: Yields bloom filters as 3-tuples
    """
    for s in dataset:
        yield crypto_bloom_filter(s, schema_types, keys, xor_folds=xor_folds)


def calculate_bloom_filters(dataset,     # type: Iterable[Tuple[Any]]
                            schema,      # type: Iterable[IdentifierType]
                            keys,        # type: Tuple[Tuple[bytes, ...]]
                            xor_folds=0  # type: int
                            ):
    # type: (...) -> List[Tuple[bitarray, Any, int]]
    """
    :param dataset: A list of indexable records.
    :param schema: An iterable of identifier types.
    :param keys: A tuple of two lists of secret keys used in the HMAC.
    :param xor_folds: number of XOR folds to perform
    :return: List of bloom filters as 3-tuples, each containing
             bloom filter (bitarray), record first element - usually index, bitcount (int)
    """
    return list(stream_bloom_filters(dataset, schema, keys, xor_folds=xor_folds))


def serialize_bitarray(ba):
    # type: (bitarray) -> str
    """Serialize a bitarray (bloomfilter)

    """
    return base64.b64encode(ba.tobytes()).decode('utf8')
