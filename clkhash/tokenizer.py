"""
Functions to tokenize words (PII)
"""
from typing import Optional, List


def unigramlist(instr, toremove=None, positional=False):
    # type: (str, Optional[List[str]], bool) -> List[str]
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


def bigramlist(word, toremove=None):
    # type: (str, Optional[List[str]]) -> List[str]
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


def positional_unigrams(instr):
    # type: (str) -> List[str]
    """
    Make positional unigrams from a word.

    E.g. 1987 -> ["1 1", "2 9", "3 8", "4 7"]

    :param instr: input string
    :return: list of strings with unigrams
    """
    return ["{index} {value}".format(index=i, value=c) for i, c in enumerate(instr, start=1)]
