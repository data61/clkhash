"""
Generate CLK from data.
"""

import csv
import logging
import sys
import time
from typing import Any, AnyStr, Callable, cast, Generator, Iterable, List, Optional, Sequence, TextIO, Tuple, TypeVar, Union

from tqdm import tqdm

from clkhash.bloomfilter import stream_bloom_filters, calculate_bloom_filters, serialize_bitarray
from clkhash.key_derivation import generate_key_lists
from clkhash.identifier_types import IdentifierType
from clkhash.schema import Schema
from clkhash.stats import OnlineMeanVariance


log = logging.getLogger('clkhash.clk')

CHUNK_SIZE = 1000


def hash_and_serialize_chunk(chunk_pii_data,  # type: Iterable[Tuple[Any]]
                             keys,            # type: Tuple[Tuple[bytes, ...], Tuple[bytes, ...]]
                             schema           # type: Schema
                             ):
    # type: (...) -> Tuple[List[str], List[int]]
    """
    Generate Bloom filters (ie hash) from chunks of PII then serialize
    the generated Bloom filters. It also computes and outputs the Hamming weight (or popcount) -- the number of bits
    set to one -- of the generated Bloom filters.

    :param chunk_pii_data: An iterable of indexable records.
    :param schema_types: An iterable of identifier type names.
    :param keys: A tuple of two lists of secret keys used in the HMAC.
    :return: A list of serialized Bloom filters and a list of corresponding popcounts
    """
    clk_data = []
    clk_popcounts = []
    for clk in stream_bloom_filters(chunk_pii_data, keys, schema_types):
        clk_data.append(serialize_bitarray(clk[0]).strip())
        clk_popcounts.append(clk[2])
    return clk_data, clk_popcounts


def generate_clk_from_csv(input_f,           # type: TextIO
                          keys,              # type: Tuple[AnyStr, AnyStr]
                          schema,            # type: clkhash.schema.Schema
                          validate=True,     # type: bool
                          header=True,       # type: bool
                          progress_bar=True  # type: bool
                          ):
    # type: (...) -> List[str]
    log.info("Hashing data")

    # Read from CSV file
    reader = csv.reader(input_f)

    if header:
        column_names = next(reader)
        if validate:
            validate_data.validate_header(schema.fields, column_names)

    start_time = time.time()

    # Read the lines in CSV file and add it to PII
    pii_data = []
    for line in reader:
        pii_data.append(line)

    # generate two keys for each identifier
    key_lists = cast(
        Tuple[Tuple[bytes, ...], Tuple[bytes, ...]],
        key_derivation.generate_key_lists(keys, len(schema.fields)))

    if progress_bar:
        stats = OnlineMeanVariance()
        with tqdm(desc="generating CLKs", total=len(pii_data), unit='clk', unit_scale=True,
                  postfix={'mean': stats.mean(), 'std': stats.std()}) as pbar:
            def callback(tics, clk_stats):
                stats.update(clk_stats)
                pbar.set_postfix(mean=stats.mean(), std=stats.std(), refresh=False)
                pbar.update(tics)

            results = generate_clks(pii_data,
                                    schema,
                                    key_lists,
                                    validate=validate,
                                    callback=callback)
    else:
        results = generate_clks(pii_data,
                                schema,
                                key_lists,
                                validate=validate)

    log.info("Hashing took {:.2f} seconds".format(time.time() - start_time))
    return results


def generate_clks(pii_data,       # type: Sequence[Sequence[str]]
                  schema,         # type: clkhash.schema.Schema
                  key_lists,      # type: Tuple[Tuple[bytes, ...], Tuple[bytes, ...]]
                  validate=True,  # type: bool
                  callback=None   # type: Optional[Callable[[int], None]]
                  ):
    # type: (...) -> List[Any]
    if validate:
        validate_data.validate_data(schema.fields, pii_data)

    # Chunks PII
    log.info("Hashing {} entities".format(len(pii_data)))
    chunk_size = 200 if len(pii_data) <= 10000 else 1000

    try:
        import concurrent.futures
    except ImportError:
        log.info("Hashing with one core, upgrade to python 3 to utilise all cores")
        stats = OnlineMeanVariance()
        for chunk in chunks(pii_data, chunk_size):
            clks, clk_stats = hash_and_serialize_chunk(chunk, schema_types, key_lists, xor_folds)
            results.extend(clks)
            stats.update(clk_stats)
            if callback is not None:
                callback(len(chunk), clk_stats)
    else:
        # If running Python3, parallelise hashing.
        # Compute Bloom filter from the chunks and then serialise it
        with concurrent.futures.ProcessPoolExecutor() as executor:
            futures = []
            for chunk in chunks(pii_data, chunk_size):
                future = executor.submit(
                    hash_and_serialize_chunk,
                    chunk, schema_types, key_lists, xor_folds)
                if callback is not None:
                    future.add_done_callback(lambda f: callback(len(f.result()[0]), f.result()[1]))
                futures.append(future)

            for future in futures:
                results.extend(future.result()[0])

    return results


T = TypeVar('T')      # Declare generic type variable


def chunks(seq, chunk_size):
    # type: (Sequence[T], int) -> Iterable[Sequence[T]]
    """ Split seq into chunk_size-sized chunks.

        :param seq: A sequence to chunk.
        :param chunk_size: The size of chunk.
    """
    return (seq[i:i + chunk_size] for i in range(0, len(seq), chunk_size))
