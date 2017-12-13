"""
Generate CLK from CSV file
"""
from tqdm import tqdm

import csv
import logging
import time

import sys

if sys.version_info[0] >= 3:
    import concurrent.futures

from clkhash.bloomfilter import stream_bloom_filters, calculate_bloom_filters, serialize_bitarray
from clkhash.key_derivation import generate_key_lists

log = logging.getLogger('clkhash.clk')


def hash_and_serialize_chunk(chunk_pii_data, schema_types, keys):
    """
    Generate Bloom filters (ie hash) from chunks of PII then serialize
    the generated Bloom filters.

    :param chunk_pii_data: An iterable of indexable records.
    :param schema_types: An iterable of identifier type names.
    :param keys: A tuple of two lists of secret keys used in the HMAC.
    :return: A list of serialized Bloom filters
    """
    clk_data = []
    for clk in stream_bloom_filters(chunk_pii_data, schema_types, keys):
        clk_data.append(serialize_bitarray(clk[0]).strip())

    return clk_data


def generate_clk_from_csv(input, keys, schema_types, no_header=False, progress_bar=True):
    log.info("Hashing data")

    # Read from CSV file
    reader = csv.reader(input)

    # Get the headers
    if not no_header:
        header = input.readline()
        log.info("Header Row: {}".format(header))

    start_time = time.time()

    # Read the lines in CSV file and add it to PII
    pii_data = []
    for line in reader:
        pii_data.append([element.strip() for element in line])

    # generate two keys for each identifier
    key_lists = generate_key_lists(keys, len(schema_types))

    if progress_bar:
        with tqdm(desc="generating CLKs", total=len(pii_data), unit='clk', unit_scale=True) as pbar:
            progress_bar_callback = lambda update: pbar.update(update)
            results = generate_clks(pii_data, schema_types, key_lists, progress_bar_callback)
    else:
        results = generate_clks(pii_data, schema_types, key_lists)

    log.info("Hashing took {:.2f} seconds".format(time.time() - start_time))
    return results


def generate_clks(pii_data, schema_types, key_lists, callback=None):
    results = []

    # Chunks PII
    log.info("Hashing {} entities".format(len(pii_data)))
    chunk_size = 200 if len(pii_data) <= 10000 else 1000

    # If running Python3 parallelise hashing.
    if sys.version_info[0] >= 3:
        # Compute Bloom filter from the chunks and then serialise it
        with concurrent.futures.ProcessPoolExecutor() as executor:
            futures = []
            for chunk in chunks(pii_data, chunk_size):
                future = executor.submit(hash_and_serialize_chunk,
                                         chunk, schema_types, key_lists)
                if callback is not None:
                    future.add_done_callback(lambda f: callback(len(f.result())))
                futures.append(future)

            for future in futures:
                results.extend(future.result())

    else:
        log.info("Hashing with one core, upgrade to python 3 to utilise all cores")
        for chunk in chunks(pii_data, chunk_size):
            results.extend(hash_and_serialize_chunk(chunk, schema_types, key_lists))
            if callback is not None:
                callback(len(chunk))
    return results


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]
