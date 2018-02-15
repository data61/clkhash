"""
Functions to tokenize words (PII)
"""
from typing import Optional, List

from future.utils import raise_from


def nullgram(word):
    return []


def positional_nullgram(word):
    return []


def unigram(word):
    return list(word)


def positional_unigrams(word):
    return ["{index} {value}".format(index=i, value=c)
            for i, c in enumerate(word, start=1)]


def bigram(word):
    word = ' {} '.format(word)
    return [word[i:i+2] for i in range(len(word)-1)]


def positional_bigram(word):
    word = ' {} '.format(word)
    return ['{} {}'.format(i + 1, word[i:i+2])
            for i in range(len(word)-1)]


# n * positional -> function
TOKENIZER_FUNCTIONS = {
    (0, False): nullgram,
    (0, True): positional_nullgram,
    (1, False): unigram,
    (1, True): positional_unigrams,
    (2, False): bigram,
    (2, True): positional_bigram,
}


def get_tokenizer(field):
    hash_settings = field.hashing_properties
    n = hash_settings.ngram
    p = hash_settings.positional

    try:
        tokenizer = TOKENIZER_FUNCTIONS[n, p]
    except KeyError as e:
        msg = ('Unsupported tokenizer configuration: n={}, positional={}.'
               .format(n, p))
        raise_from(ValueError(msg), e)

    return tokenizer
