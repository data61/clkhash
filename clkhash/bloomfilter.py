#!/usr/bin/env python3

"""
Generate a Bloom filter
"""

import hmac
import math
import struct
from functools import lru_cache
from hashlib import md5, sha1
from typing import Callable, Iterable, List, Sequence, Tuple
from bitarray import bitarray

from clkhash.field_formats import FieldHashingProperties
from clkhash.schema import Schema
from clkhash.comparators import AbstractComparison, NonComparison

try:
    from hashlib import blake2b
except ImportError:
    # We are in Python older than 3.6.
    from pyblake2 import blake2b  # type: ignore
    # Ignore because otherwise Mypy raises errors, thinking that
    # blake2b is already defined.


TOKEN_CACHE_SIZE = 2 ** 15
NGRAM_CACHE_SIZE = 2 ** 17


def double_hash_encode_ngrams(ngrams: Iterable[str],
                              keys: Sequence[bytes],
                              ks: Sequence[int],
                              l: int,
                              encoding: str
                              ) -> bitarray:
    """ Computes the double hash encoding of the ngrams with the given keys.

        Using the method from [Schnell2011]_.

        :param ngrams: list of n-grams to be encoded
        :param keys: hmac secret keys for md5 and sha1 as bytes
        :param ks: ks[i] is k value to use for ngram[i]
        :param l: length of the output bitarray
        :param encoding: the encoding to use when turning the ngrams to bytes

        :return: bitarray of length l with the bits set which correspond to
                 the encoding of the ngrams
    """
    return _double_hash_encode_ngrams(tuple(ngrams), (keys[0], keys[1]), tuple(ks), l, encoding, non_singular=False)


def double_hash_encode_ngrams_non_singular(ngrams: Iterable[str],
                                           keys: Sequence[bytes],
                                           ks: Sequence[int],
                                           l: int,
                                           encoding: str
                                           ) -> bitarray:
    """ Computes the double hash encoding of the n-grams with the given keys.

        The original construction of [Schnell2011]_ displays an abnormality for
        certain inputs:

            An n-gram can be encoded into just one bit irrespective of the number
            of k.

        Their construction goes as follows: the :math:`k` different indices
        :math:`g_i` of the Bloom filter for an n-gram
        :math:`x` are defined as:

        .. math:: g_{i}(x) = (h_1(x) + i h_2(x)) \\mod l

        with :math:`0 \\leq i < k` and :math:`l` is the length of the Bloom
        filter. If the value of the hash of :math:`x` of
        the second hash function is a multiple of :math:`l`, then

        .. math:: h_2(x) = 0 \\mod l

        and thus

        .. math:: g_i(x) = h_1(x) \\mod l,

        irrespective of the value :math:`i`. A discussion of this potential flaw
        can be found
        `here <https://github.com/data61/clkhash/issues/33>`_.

        :param ngrams: list of n-grams to be encoded
        :param keys: tuple with (key_sha1, key_md5).
               That is, (hmac secret keys for sha1 as bytes, hmac secret keys for
               md5 as bytes)
        :param ks: ks[i] is k value to use for ngram[i]
        :param l: length of the output bitarray
        :param encoding: the encoding to use when turning the ngrams to bytes

        :return: bitarray of length l with the bits set which correspond to the
                 encoding of the ngrams
    """
    return _double_hash_encode_ngrams(tuple(ngrams), (keys[0], keys[1]), tuple(ks), l, encoding, non_singular=True)


@lru_cache(maxsize=NGRAM_CACHE_SIZE)
def _double_hash_encode_ngrams(ngrams: Tuple[str, ...],
                               keys: Tuple[bytes, bytes],
                               ks: Tuple[int, ...],
                               l: int,
                               encoding: str,
                               non_singular: bool
                              ) -> bitarray:
    key_sha1, key_md5 = keys
    bf = bitarray(l)
    bf.setall(False)

    for m, k in zip(ngrams, ks):
        m_bytes = m.encode(encoding=encoding)
        if non_singular:
            md5hm, sha1hm = _double_hash_token_non_singular(m_bytes, l, key_sha1, key_md5)
        else:
            md5hm, sha1hm = _double_hash_token(m_bytes, l, key_sha1, key_md5)
        for i in range(k):
            gi = (sha1hm + i * md5hm) % l
            bf[gi] = 1
    return bf


@lru_cache(maxsize=TOKEN_CACHE_SIZE)
def _double_hash_token(m: bytes, l: int, key_sha1: bytes, key_md5: bytes):
    sha1hm = int(
        hmac.new(key_sha1, m, sha1).hexdigest(),
        16) % l
    md5hm = int(
        hmac.new(key_md5, m, md5).hexdigest(),
        16) % l
    return md5hm, sha1hm


@lru_cache(maxsize=TOKEN_CACHE_SIZE)
def _double_hash_token_non_singular(m_bytes: bytes, l: int, key_sha1: bytes, key_md5: bytes):
    sha1hm_bytes = hmac.new(key_sha1, m_bytes, sha1).digest()
    md5hm_bytes = hmac.new(key_md5, m_bytes, md5).digest()
    sha1hm = int.from_bytes(sha1hm_bytes, 'big') % l
    md5hm = int.from_bytes(md5hm_bytes, 'big') % l
    i = 0
    while md5hm == 0:
        md5hm_bytes = hmac.new(
            key_md5, m_bytes + chr(i).encode(), md5).digest()
        md5hm = int.from_bytes(md5hm_bytes, 'big') % l
        i += 1
    return md5hm, sha1hm


def blake_encode_ngrams(ngrams: Iterable[str],
                        keys: Sequence[bytes],
                        ks: Sequence[int],
                        l: int,
                        encoding: str,
                        ) -> bitarray:
    """ Computes the encoding of the ngrams using the BLAKE2 hash function.

        We deliberately do not use the double hashing scheme as proposed in
        [Schnell2011]_, because this would introduce an exploitable structure
        into the Bloom filter. For more details on the weakness, see [Kroll2015]_.

        In short, the double hashing scheme only allows for :math:`l^2`
        different encodings for any possible n-gram,
        whereas the use of :math:`k` different independent hash functions gives
        you :math:`\\sum_{j=1}^{k}{\\binom{l}{j}}`
        combinations.


        **Our construction**

        It is advantageous to construct Bloom filters using a family of hash
        functions with the property of
        `k-independence <https://en.wikipedia.org/wiki/K-independent_hashing>`_
        to compute the indices for an entry.
        This approach minimises the change of collisions.

        An informal definition of *k-independence* of a family of hash functions
        is, that if selecting a function at random
        from the family, it guarantees that the hash codes of any designated k
        keys are independent random variables.

        Our construction utilises the fact that the output bits of a
        cryptographic hash function are uniformly distributed,
        independent, binary random variables (well, at least as close to as
        possible. See [Kaminsky2011]_ for an analysis).
        Thus, slicing the output of a cryptographic hash function into k
        different slices gives you k independent random
        variables.

        We chose Blake2 as the cryptographic hash function mainly for two reasons:

        * it is fast.
        * in keyed hashing mode, Blake2 provides MACs with just one hash
          function call instead of the two calls in the HMAC construction used
          in the double hashing scheme.


        .. warning::
           Please be aware that, although this construction makes the attack of
           [Kroll2015]_ infeasible, it is most likely
           not enough to ensure security. Or in their own words:

             | However, we think that using independent hash functions alone
               will not be sufficient to ensure security,
               since in this case other approaches (maybe related to or at least
               inspired through work from the
               area of Frequent Itemset Mining) are promising to detect at least
               the most frequent atoms automatically.

        :param ngrams: list of n-grams to be encoded
        :param keys: secret key for blake2 as bytes
        :param ks: ks[i] is k value to use for ngram[i]
        :param l: length of the output bitarray (has to be a power of 2)
        :param encoding: the encoding to use when turning the ngrams to bytes

        :return: bitarray of length l with the bits set which correspond to the
                 encoding of the ngrams
    """
    key = bytes(keys[0])  # We only need the first key
    return _blake_encode_ngrams(tuple(ngrams), key, tuple(ks), l, encoding)


@lru_cache(maxsize=NGRAM_CACHE_SIZE)
def _blake_encode_ngrams(ngrams: Tuple[str, ...],
                         key: bytes,
                         ks: Tuple[int, ...],
                         l: int,
                         encoding: str,
                         ) -> bitarray:
    log_l = int(math.log(l, 2))
    if not 2 ** log_l == l:
        raise ValueError(
            'parameter "l" has to be a power of two for the BLAKE2 encoding, '
            'but was: {}'.format(
                l))
    bf = bitarray(l)
    bf.setall(False)

    for m, k in zip(ngrams, ks):
        for idx in blake_hash_token(m.encode(encoding=encoding), k, key, l):
            bf[idx] = 1
    return bf


@lru_cache(maxsize=TOKEN_CACHE_SIZE)
def blake_hash_token(token: bytes, k: int, key: bytes, l: int):
    random_shorts = []  # type: List[int]
    num_macs = (k + 31) // 32
    for i in range(num_macs):
        hash_bytes = blake2b(token, key=key,
                             salt=str(i).encode()).digest()
        random_shorts.extend(struct.unpack('32H',
                                           hash_bytes))  # interpret
        # hash bytes as 32 unsigned shorts.
    return [random_shorts[i] % l for i in range(k)]


def hashing_function_from_properties(
        fhp: FieldHashingProperties
        ) -> Callable[[Iterable[str], Sequence[bytes], Sequence[int], int, str], bitarray]:
    """ Get the hashing function for this field
        :param fhp: hashing properties for this field
        :return: the hashing function
    """
    if fhp.hash_type == 'doubleHash':
        if fhp.prevent_singularity:
            return double_hash_encode_ngrams_non_singular
        else:
            return double_hash_encode_ngrams
    elif fhp.hash_type == 'blakeHash':
        return blake_encode_ngrams
    else:
        msg = f"Unsupported hash type '{fhp.hash_type}'"
        raise ValueError(msg)


def fold_xor(bloomfilter: bitarray,
             folds: int
             ) -> bitarray:
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


def crypto_bloom_filter(record: Sequence[str],
                        comparators: List[AbstractComparison],
                        schema: Schema,
                        keys: Sequence[Sequence[bytes]],
                        ) -> Tuple[bitarray, str, int]:
    """ Computes the composite Bloom filter encoding of a record.

    Based on the method from [Schnell2011]_.

    :param record: plaintext record tuple. E.g. (index, name, dob, gender)
    :param comparators: A list of comparators. They provide a 'tokenize' function to turn string into
        appropriate tokens.
    :param schema: The Linkage Schema describing how to encode plaintext identifiers.
    :param keys: Keys for the hash functions as a tuple of lists of bytes.

    :return: 3-tuple:

        - bloom filter for record as a bitarray
        - first element of record (usually an index)
        - number of bits set in the bloomfilter
    """
    hash_l = schema.l * 2 ** schema.xor_folds

    bloomfilter = bitarray(hash_l)
    bloomfilter.setall(False)

    for (entry, comparator, field, key) \
            in zip(record, comparators, schema.fields, keys):
        fhp = field.hashing_properties
        if fhp:
            ngrams = list(comparator.tokenize(field.format_value(entry)))
            hash_function = hashing_function_from_properties(fhp)

            if ngrams:
                bloomfilter |= hash_function(ngrams, key,
                                             fhp.strategy.bits_per_token(len(ngrams)),
                                             hash_l, fhp.encoding)

    bloomfilter = fold_xor(bloomfilter, schema.xor_folds)
    return bloomfilter, record[0], bloomfilter.count()


def stream_bloom_filters(dataset: Iterable[Sequence[str]],
                         keys: Sequence[Sequence[bytes]],
                         schema: Schema
                         ) -> Iterable[Tuple[bitarray, str, int]]:
    """ Compute composite Bloom filters (CLKs) for every record in an
        iterable dataset.

        :param dataset: An iterable of indexable records.
        :param schema: An instantiated Schema instance
        :param keys: A tuple of two lists of secret keys used in the HMAC.
        :return: Generator yielding bloom filters as 3-tuples
    """
    comparators = [field.hashing_properties.comparator if field.hashing_properties is not None else NonComparison()
                  for field in schema.fields]
    return (crypto_bloom_filter(s, comparators, schema, keys)
            for s in dataset)
