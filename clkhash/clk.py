# -*- coding: utf-8 -*-

"""
Generate CLK from data.
"""

import concurrent.futures
import csv
import logging
import sys
import time
from typing import (Any, Callable, Generator, Iterable, List,
                    Optional, Sequence, TextIO, Tuple, TypeVar, Union)

from tqdm import tqdm

from clkhash import bloomfilter, key_derivation, validate_data

log = logging.getLogger('clkhash.clk')


def hash_and_serialize_chunk(chunk_pii_data,    # type: Iterable[Tuple[Any]]
                             keys,              # type: Tuple[Tuple[bytes, ...], Tuple[bytes, ...]]
                             schema
                             ):
    # type: (...) -> List[str]
    """
    Generate Bloom filters (ie hash) from chunks of PII then serialize
    the generated Bloom filters.

    :param chunk_pii_data: An iterable of indexable records.
    :param schema_types: An iterable of identifier type names.
    :param keys: A tuple of two lists of secret keys used in the HMAC.
    :return: A list of serialized Bloom filters
    """
    clk_data = []
    for clk in bloomfilter.stream_bloom_filters(chunk_pii_data, keys, schema):
        clk_data.append(bloomfilter.serialize_bitarray(clk[0]).strip())

    return clk_data


def generate_clk_from_csv(input_f,          # type: TextIO
                          keys,             # type: Tuple[Union[bytes, str], Union[bytes, str]]
                          schema,
                          validate=True,    # type: bool
                          header=True,      # type: bool
                          progress_bar=True # type: bool
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
    key_lists = key_derivation.generate_key_lists(keys, len(schema.fields))

    if progress_bar:
        with tqdm(desc="generating CLKs",
                  total=len(pii_data),
                  unit='clk',
                  unit_scale=True) as pbar:
            progress_bar_callback = lambda update: pbar.update(update)
            results = generate_clks(pii_data,
                                    schema,
                                    key_lists,
                                    validate=validate,
                                    callback=progress_bar_callback)
    else:
        results = generate_clks(pii_data,
                                schema,
                                key_lists,
                                validate=validate)

    log.info("Hashing took {:.2f} seconds".format(time.time() - start_time))
    return results


def generate_clks(pii_data,       # type: Sequence[Sequence[str, ...]]
                  schema,
                  key_lists,      # type: Tuple[Tuple[bytes, ...], ...]
                  validate=True,  # type: bool
                  callback=None   # type: Optional[Callable[[int], None]]
                  ):
    # type: (...) -> List[Any]
    if validate:
        validate_data.validate_data(schema.fields, pii_data)

    results = []

    # Chunks PII
    log.info("Hashing {} entities".format(len(pii_data)))
    chunk_size = 200 if len(pii_data) <= 10000 else 1000

    # Compute Bloom filter from the chunks and then serialise it
    with concurrent.futures.ProcessPoolExecutor() as executor:
        futures = []
        for chunk in chunks(pii_data, chunk_size):
            future = executor.submit(hash_and_serialize_chunk,
                                     chunk, key_lists, schema)
            if callback is not None:
                future.add_done_callback(lambda f: callback(len(f.result())))
            futures.append(future)

        for future in futures:
            results.extend(future.result())

    return results


T = TypeVar('T')  # Declare generic type.
def chunks(seq, chunk_size):
    # type: (Sequence[T], int) -> Iterable[Sequence[T]]
    """ Split seq into chunk_size-sized chunks.

        :param seq: A sequence to chunk.
        :param chunk_size: The size of chunk.
    """
    return (seq[i:i + chunk_size] for i in range(0, len(seq), chunk_size))
