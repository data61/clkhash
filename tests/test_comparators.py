import decimal
import itertools
import random

import pytest
from hypothesis import given, assume
from hypothesis.strategies import text, integers, decimals
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


@given(thresh_dist=integers(min_value=1, max_value=28).flatmap(
           lambda i: decimals(allow_infinity=False, allow_nan=False, min_value=0.0, places=i)),
       resolution=integers(min_value=1, max_value=512),
       candidate=integers(min_value=1, max_value=28).flatmap(
           lambda p: decimals(allow_infinity=False, allow_nan=False, places=p)))
def test_numeric_properties(thresh_dist, resolution, candidate):
    assume(thresh_dist > 0)
    assume(abs(candidate.adjusted() - thresh_dist.adjusted()) <= 28)
    tokens = NumericComparison(thresh_dist, resolution).tokenize(str(candidate))
    assert len(tokens) == 2 * resolution + 1, "unexpected number of tokens"
    tokens_again = NumericComparison(thresh_dist, resolution).tokenize(str(candidate))
    assert tokens == tokens_again, "NumericComparison should be deterministic"
    assert len(set(tokens)) == 2 * resolution + 1, "tokens should be unique"


@given(thresh_dist=integers(min_value=1, max_value=28).flatmap(
           lambda i: decimals(allow_infinity=False, allow_nan=False, min_value=0.0, places=i)),
       resolution=integers(min_value=1, max_value=512),
       candidate=integers(min_value=1, max_value=28).flatmap(
           lambda p: decimals(allow_infinity=False, allow_nan=False, places=p)))
def test_numeric_overlaps(thresh_dist, resolution, candidate):
    assume(abs(candidate.adjusted()-thresh_dist.adjusted()) < 28)
    comp = NumericComparison(threshold_distance=thresh_dist, resolution=resolution)
    assume(thresh_dist > 0)
    other = comp.context.add(candidate, thresh_dist)
    cand_tokens = comp.tokenize(candidate)
    other_tokens = comp.tokenize(other)
    assert len(set(cand_tokens).intersection(
        set(other_tokens))) == 1, "numbers exactly thresh_dist apart have 1 token in common"
    other = candidate + thresh_dist * decimal.Decimal('1.51')  # 0.5 because of the modulo operation
    other_tokens = comp.tokenize(other)
    assert len(set(cand_tokens).intersection(
        set(other_tokens))) == 0, "numbers more than thresh_dist apart have no tokens in common"
    other = candidate + (thresh_dist / decimal.Decimal(2 * resolution)) * decimal.Decimal(random.random())
    other_tokens = comp.tokenize(other)
    assert len(set(cand_tokens).intersection(
        set(other_tokens))) >= len(
        cand_tokens) - 2, "numbers that are not more than the modulus apart have all or all - 2 tokens in common"
    numbers = [comp.context.add(candidate, comp.context.multiply(thresh_dist, decimal.Decimal(str(i * 0.1)))) for i in range(20)]

    def overlap(other):
        other_tokens = comp.tokenize(other)
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
