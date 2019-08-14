import itertools

import pytest
from hypothesis import given, assume
from hypothesis.strategies import text, integers
from pytest import fixture

from clkhash import comparators
from clkhash.comparators import NgramComparison, NonComparison, ExactComparison


#######
# Testing n-gram
#######


@fixture(params=itertools.product((1, 2, 3), (True, False)))
def ngram_comparator(request):
    return comparators.NgramComparison(request.param[0], request.param[1])


@given(myinput=text(min_size=1))
def test_bigram_encoding_deterministic(myinput, ngram_comparator):
    assert set(ngram_comparator.tokenize(myinput)) == set(ngram_comparator.tokenize(myinput))


@given(text(min_size=1))
def test_ngram_spaces(ngram_comparator, myinput):
    tokens = list(ngram_comparator.tokenize(myinput))
    assert tokens[0].endswith(' ' * (ngram_comparator.n - 1) + myinput[0])
    assert tokens[-1].endswith(myinput[-1] + ' ' * (ngram_comparator.n - 1))


@given(text(min_size=1))
def test_string_bigram_token_size(ngram_comparator, myinput):
    tokens = list(ngram_comparator.tokenize(myinput))
    assert len(myinput) == len(tokens) - (ngram_comparator.n - 1)


def test_invalid_n():
    with pytest.raises(ValueError):
        comparators.get_comparator({'type': 'ngram', 'n': -6})


@given(word=text(), n=integers(min_value=1, max_value=3))
def test_positional(word, n):
    tokenizer = NgramComparison(n, True).tokenize
    tokens = list(tokenizer(word))
    indices = set(int(token.split(' ')[0]) for token in tokens)  # a token begins with the index followed by space
    assert indices == set(range(1, len(tokens) + 1))


def test_empty_input(ngram_comparator):
    assert list(ngram_comparator.tokenize("")) == []


#####
# testing the Non-Comparison
#####


def test_dummy():
    comp = NonComparison()
    assert list(NonComparison().tokenize('jobs')) == []


#####
# testing exact comparison
#####


@given(word=text())
def test_exact_deterministic(word):
    assert ExactComparison().tokenize(word) == ExactComparison().tokenize(word)


@given(word1=text(), word2=text())
def test_exact_uniqueness(word1, word2):
    assume(word1 != word2)
    assert set(list(ExactComparison().tokenize(word1))) != set(list(ExactComparison().tokenize(word2)))


@given(word=text())
def test_exact_num_tokens(word):
    assert len(list(ExactComparison().tokenize(word))) == 1


#####
# testing invalid comparison
#####


def test_invalid_comparison():
    with pytest.raises(ValueError):
        comparators.get_comparator({"type": "apples_and_oranges"})
