#!/usr/bin/env python3

"""
Generate a Bloom filter
"""

import hmac
import math
import struct
from hashlib import md5, sha1
from typing import Callable, Iterable, List, Optional, Sequence, Text, Tuple
from bitarray import bitarray
from future.builtins import range, zip

from clkhash import tokenizer
from clkhash.backports import int_from_bytes
from clkhash.field_formats import FieldHashingProperties
from clkhash.schema import Schema

try:
    from hashlib import blake2b
except ImportError:
    # We are in Python older than 3.6.
    from pyblake2 import blake2b  # type: ignore
    # Ignore because otherwise Mypy raises errors, thinking that
    # blake2b is already defined.


def double_hash_encode_ngrams(ngrams,   # type: Iterable[str]
                              keys,     # type: Sequence[bytes]
                              ks,       # type: Sequence[int]
                              l,        # type: int
                              encoding  # type: str
                              ):
    # type: (...) -> bitarray
    """ Computes the double hash encoding of the ngrams with the given keys.

            Using the method from:
            Schnell, R., Bachteler, T., & Reiher, J. (2011).
            A Novel Error-Tolerant Anonymous Linking Code.
            http://grlc.german-microsimulation.de/wp-content/uploads/2017/05/downloadwp-grlc-2011-02.pdf

        :param ngrams: list of n-grams to be encoded
        :param keys: hmac secret keys for md5 and sha1 as bytes
        :param ks: ks[i] is k value to use for ngram[i]
        :param l: length of the output bitarray
        :param encoding: the encoding to use when turning the ngrams to bytes

        :return: bitarray of length l with the bits set which correspond to
                 the encoding of the ngrams
    """
    key_sha1, key_md5 = keys
    bf = bitarray(l)
    bf.setall(False)

    for m, k in zip(ngrams, ks):
        sha1hm = int(
            hmac.new(key_sha1, m.encode(encoding=encoding), sha1).hexdigest(),
            16) % l
        md5hm = int(
            hmac.new(key_md5, m.encode(encoding=encoding), md5).hexdigest(),
            16) % l
        for i in range(k):
            gi = (sha1hm + i * md5hm) % l
            bf[gi] = 1
    return bf


def double_hash_encode_ngrams_non_singular(ngrams,   # type: Iterable[str]
                                           keys,     # type: Sequence[bytes]
                                           ks,       # type: Sequence[int]
                                           l,        # type: int
                                           encoding  # type: str
                                           ):
    # type: (...) -> bitarray.bitarray
    """ computes the double hash encoding of the n-grams with the given keys.

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
    key_sha1, key_md5 = keys
    bf = bitarray(l)
    bf.setall(False)
    for m, k in zip(ngrams, ks):
        m_bytes = m.encode(encoding=encoding)

        sha1hm_bytes = hmac.new(key_sha1, m_bytes, sha1).digest()
        md5hm_bytes = hmac.new(key_md5, m_bytes, md5).digest()

        sha1hm = int_from_bytes(sha1hm_bytes, 'big') % l
        md5hm = int_from_bytes(md5hm_bytes, 'big') % l

        i = 0
        while md5hm == 0:
            md5hm_bytes = hmac.new(
                key_md5, m_bytes + chr(i).encode(), md5).digest()
            md5hm = int_from_bytes(md5hm_bytes, 'big') % l
            i += 1

        for i in range(k):
            gi = (sha1hm + i * md5hm) % l
            bf[gi] = True
    return bf


def blake_encode_ngrams(ngrams,   # type: Iterable[str]
                        keys,     # type: Sequence[bytes]
                        ks,       # type: Sequence[int]
                        l,        # type: int
                        encoding  # type: str
                        ):
    # type: (...) -> bitarray.bitarray
    """ Computes the encoding of the ngrams using the BLAKE2 hash function.

        We deliberately do not use the double hashing scheme as proposed in [
        Schnell2011]_, because this
        would introduce an exploitable structure into the Bloom filter. For more
        details on the
        weakness, see [Kroll2015]_.

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
    key = keys[0]  # We only need the first key

    log_l = int(math.log(l, 2))
    if not 2 ** log_l == l:
        raise ValueError(
            'parameter "l" has to be a power of two for the BLAKE2 encoding, '
            'but was: {}'.format(
                l))
    bf = bitarray(l)
    bf.setall(False)

    for m, k in zip(ngrams, ks):
        random_shorts = []  # type: List[int]
        num_macs = (k + 31) // 32
        for i in range(num_macs):
            hash_bytes = blake2b(m.encode(encoding=encoding), key=key,
                                 salt=str(i).encode()).digest()
            random_shorts.extend(struct.unpack('32H',
                                               hash_bytes))  # interpret
            # hash bytes as 32 unsigned shorts.
        for i in range(k):
            idx = random_shorts[i] % l
            bf[idx] = 1
    return bf


def hashing_function_from_properties(
        fhp  # type: FieldHashingProperties
        ):
    # type: (...) -> Callable[[Iterable[str], Sequence[bytes], Sequence[int], int, str], bitarray]
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
        msg = "Unsupported hash type '{}'".format(fhp.hash_type)
        raise ValueError(msg)


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


def crypto_bloom_filter(record,      # type: Sequence[Text]
                        tokenizers,  # type: List[Callable[[Text, Optional[Text]], Iterable[Text]]]
                        schema,      # type: Schema
                        keys         # type: Sequence[Sequence[bytes]]
                        ):
    # type: (...) -> Tuple[bitarray, Text, int]
    """ Computes the composite Bloom filter encoding of a record.

        Using the method from
        http://www.record-linkage.de/-download=wp-grlc-2011-02.pdf

        :param record: plaintext record tuple. E.g. (index, name, dob, gender)
        :param tokenizers: A list of tokenizers. A tokenizer is a function that
            returns tokens from a string.
        :param schema: Schema
        :param keys: Keys for the hash functions as a tuple of lists of bytes.

        :return: 3-tuple:
                - bloom filter for record as a bitarray
                - first element of record (usually an index)
                - number of bits set in the bloomfilter
    """
    hash_l = schema.l * 2 ** schema.xor_folds

    bloomfilter = bitarray(hash_l)
    bloomfilter.setall(False)

    for (entry, tokenize, field, key) \
            in zip(record, tokenizers, schema.fields, keys):
        fhp = field.hashing_properties
        if fhp:
            ngrams = list(tokenize(field.format_value(entry)))
            hash_function = hashing_function_from_properties(fhp)
            bloomfilter |= hash_function(ngrams, key,
                                         fhp.ks(len(ngrams)),
                                         hash_l, fhp.encoding)

    c1 = bloomfilter.count()
    bloomfilter = fold_xor(bloomfilter, schema.xor_folds)
    c2 = bloomfilter.count()
    return bloomfilter, record[0], bloomfilter.count()


def stream_bloom_filters(dataset,  # type: Iterable[Sequence[Text]]
                         keys,     # type: Sequence[Sequence[bytes]]
                         schema    # type: Schema
                         ):
    # type: (...) -> Iterable[Tuple[bitarray, Text, int]]
    """ Compute composite Bloom filters (CLKs) for every record in an
        iterable dataset.

        :param dataset: An iterable of indexable records.
        :param schema: An instantiated Schema instance
        :param keys: A tuple of two lists of secret keys used in the HMAC.
        :return: Generator yielding bloom filters as 3-tuples
    """
    tokenizers = [tokenizer.get_tokenizer(field.hashing_properties)
                  for field in schema.fields]
    return (crypto_bloom_filter(s, tokenizers, schema, keys)
            for s in dataset)
