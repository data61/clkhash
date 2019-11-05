from __future__ import division
import itertools
import random
import math

import pytest
from hypothesis import given, assume
from hypothesis.strategies import text, integers, floats
from pytest import fixture

from clkhash import comparators
from clkhash.comparators import NgramComparison, NonComparison, ExactComparison, NumericComparison


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
# testing numeric comparison
#####

# we restrict the exponents of the floats such that exponent of number + precision <= 308. Otherwise we might get
# infinity during the tokenization process.
@given(thresh_dist=floats(min_value=0.0, allow_nan=False, allow_infinity=False, max_value=1e288),
       resolution=integers(min_value=1, max_value=512),
       precision=integers(min_value=0, max_value=20),
       candidate=floats(allow_nan=False, allow_infinity=False, max_value=1e288, min_value=-1e288))
def test_numeric_properties(thresh_dist, resolution, precision, candidate):
    assume(thresh_dist > 0)
    adj_dist = thresh_dist * pow(10, precision)
    if int(round(adj_dist)) <= 0:
        with pytest.raises(ValueError):
            NumericComparison(thresh_dist, resolution, precision)
    else:
        tokens = NumericComparison(thresh_dist, resolution, precision).tokenize(str(candidate))
        assert len(tokens) == 2 * resolution + 1, "unexpected number of tokens"
        tokens_again = NumericComparison(thresh_dist, resolution, precision).tokenize(str(candidate))
        assert tokens == tokens_again, "NumericComparison should be deterministic"
        assert len(set(tokens)) == 2 * resolution + 1, "tokens should be unique"


@given(thresh_dist=floats(allow_infinity=False, allow_nan=False, min_value=0.0, max_value=1e288),
       resolution=integers(min_value=1, max_value=512),
       precision=integers(min_value=0, max_value=20),
       candidate=floats(allow_infinity=False, allow_nan=False, max_value=1e288, min_value=-1e288))
def test_numeric_overlaps(thresh_dist, resolution, precision, candidate):
    assume(thresh_dist > 0)
    assume(int(round(thresh_dist * pow(10, precision))) > 0)
    comp = NumericComparison(threshold_distance=thresh_dist, resolution=resolution, fractional_precision=precision)
    other = candidate + thresh_dist
    cand_tokens = comp.tokenize(str(candidate))
    other_tokens = comp.tokenize(str(other))
    if other != candidate:
        assert len(set(cand_tokens).intersection(
            set(other_tokens))) == 1, "numbers exactly thresh_dist apart have 1 token in common"
    other = candidate + thresh_dist * 1.51  # 0.5 because of the modulo operation
    assume((other - candidate) > (1.5 * thresh_dist))  # because of fp precision errors, 'other might not have changed'
    other_tokens = comp.tokenize(str(other))
    assert len(set(cand_tokens).intersection(
        set(other_tokens))) == 0, "numbers more than thresh_dist apart have no tokens in common"
    other = candidate + int((thresh_dist / (2 * resolution) * random.random()))
    other_tokens = comp.tokenize(str(other))
    assert len(set(cand_tokens).intersection(
        set(other_tokens))) >= len(
        cand_tokens) - 2, "numbers that are not more than the modulus apart have all or all - 2 tokens in common"
    numbers = [candidate + thresh_dist * (i * 0.1) for i in range(20)]

    def overlap(other):
        other_tokens = comp.tokenize(str(other))
        return len(set(cand_tokens).intersection(set(other_tokens)))
    overlaps = [overlap(num) for num in numbers]
    assert overlaps[0] == len(cand_tokens)
    assert overlaps[-1] == 0
    assert all(x >= y for x, y in zip(overlaps, overlaps[1:])), 'with increasing distance, the overlap reduces'


@given(thresh_dist=integers(min_value=1),
       resolution=integers(min_value=1, max_value=512),
       candidate=integers())
def test_numeric_properties_with_integers(thresh_dist, resolution, candidate):
    tokens = NumericComparison(thresh_dist, resolution).tokenize(str(candidate))
    assert len(tokens) == 2 * resolution + 1, "unexpected number of tokens"
    tokens_again = NumericComparison(thresh_dist, resolution).tokenize(str(candidate))
    assert tokens == tokens_again, "NumericComparison should be deterministic"
    assert len(set(tokens)) == 2 * resolution + 1, "tokens should be unique"


@given(thresh_dist=integers(min_value=1),
       resolution=integers(min_value=1, max_value=512),
       candidate=integers())
def test_numeric_overlaps_with_integers(thresh_dist, resolution, candidate):
    comp = NumericComparison(threshold_distance=thresh_dist, resolution=resolution, fractional_precision=0)
    other = candidate + thresh_dist
    cand_tokens = comp.tokenize(str(candidate))
    other_tokens = comp.tokenize(str(other))
    if other != candidate:
        assert len(set(cand_tokens).intersection(
            set(other_tokens))) == 1, "numbers exactly thresh_dist apart have 1 token in common"
    other = candidate + thresh_dist + int(math.ceil(thresh_dist/2))
    other_tokens = comp.tokenize(str(other))
    assert len(set(cand_tokens).intersection(
        set(other_tokens))) == 0, "numbers more than thresh_dist apart have no tokens in common"
    modulus = int(thresh_dist / (2 * resolution))
    if modulus > 0:
        other = candidate + random.randrange(modulus)
        other_tokens = comp.tokenize(str(other))
        assert len(set(cand_tokens).intersection(
            set(other_tokens))) >= len(
            cand_tokens) - 2, "numbers that are not more than the modulus apart have all or all - 2 tokens in common"

    if thresh_dist < 20:
        numbers = [candidate + i for i in range(thresh_dist + 10)]
    else:
        numbers = [candidate + int(thresh_dist * (i * 0.1)) for i in range(20)]
    def overlap(other):
        other_tokens = comp.tokenize(str(other))
        return len(set(cand_tokens).intersection(set(other_tokens)))
    overlaps = [overlap(num) for num in numbers]
    assert overlaps[0] == len(cand_tokens)
    assert overlaps[-1] == 0
    assert all(x >= y for x, y in zip(overlaps, overlaps[1:])), 'with increasing distance, the overlap reduces'


#####
# testing invalid comparison
#####


def test_invalid_comparison():
    with pytest.raises(ValueError):
        comparators.get_comparator({"type": "apples_and_oranges"})
