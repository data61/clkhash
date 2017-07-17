from hashlib import sha1, md5
import hmac
from bitarray import bitarray
# from anonlink._entitymatcher import ffi, lib

__author__ = 'shardy'


def hbloom(mlist, l=1024, k=30, keysha1="secret1", keymd5="secret2"):
    """
    Cryptographic bloom filter for list of strings

    :param mlist: list of strings to be hashed and encoded in filter
    :param l: length of filter
    :param k: number of hash functions to use per element
    :param keysha1: hmac secret key for sha1
    :param keymd5: hmac secret key for md5
    :return: bitarray with bloom filter
    """
    bf = bitarray(l)
    bf[:] = 0
    for m in mlist:
        sha1hm = int(hmac.new(keysha1.encode(), m.encode(), sha1).hexdigest(), 16) % l
        md5hm = int(hmac.new(keymd5.encode(), m.encode(), md5).hexdigest(), 16) % l
        for i in range(k):
            gi = (sha1hm + i * md5hm) % l
            bf[gi] = 1
    return bf


def bigramlist(word, toremove=None):
    """
    Make bigrams from word with pre- and ap-pended spaces

    s -> [' ' + s0, s0 + s1, s1 + s2, .. sN + ' ']

    :param word: string to make bigrams from
    :param toremove: List of strings to remove before construction
    :return: list of bigrams as strings
    """
    if toremove is not None:
        for substr in toremove:
            word = word.replace(substr, "")
    word = " " + word + " "
    return [word[i:i+2] for i in range(len(word)-1)]


def unigramlist(instr, toremove=None, positional=False):
    """
    Make 1-grams (unigrams) from a word, possibly excluding particular substrings

    :param instr: input string
    :param toremove: Iterable of strings to remove
    :return: list of strings with unigrams
    """
    if toremove is not None:
        for substr in toremove:
            instr = instr.replace(substr, "")

    if positional:
        return positional_unigrams(instr)
    else:
        return list(instr)


def positional_unigrams(instr):
    """
    Make positional unigrams from a word.

    E.g. 1987 -> ["1 1", "2 9", "3 8", "4 7"]

    :param instr: input string
    :return: list of strings with unigrams
    """
    return ["{index} {value}".format(index=i, value=c) for i, c in enumerate(instr, start=1)]

