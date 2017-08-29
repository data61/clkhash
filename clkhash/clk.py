"""
Generate CLK from CSV file
"""
import csv
import logging
import time

import sys

if sys.version_info[0] >= 3:
    import concurrent.futures

from clkhash.bloomfilter import stream_bloom_filters, calculate_bloom_filters, serialize_bitarray

log = logging.getLogger('clkhash.clk')


def hash_and_serialize_chunk(chunk_pii_data, schema_types, keys):
    """
    Generate Bloom filters (ie hash) from chunks of PII then serialize
    the generated Bloom filters.

    :param chunk_pii_data: An iterable of indexable records.
    :param schema_types: An iterable of identifier type names.
    :param keys: A tuple of two secret keys used in the HMAC.
    :return: A list of serialized Bloom filters
    """
    clk_data = []
    for clk in stream_bloom_filters(chunk_pii_data, schema_types, keys):
        clk_data.append(serialize_bitarray(clk[0]).strip())

    return clk_data


def generate_clk_from_csv(input, keys, schema_types, no_header=False):
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

    # Chunks PII
    log.info("Hashing {} entities".format(len(pii_data)))
    chunk_size = 1000 if len(pii_data) <= 10000 else 10000

    results = []
    # If running Python3 parallelise hashing.
    if sys.version_info[0] >= 3:
        # Compute Bloom filter from the chunks and then serialise it
        with concurrent.futures.ProcessPoolExecutor() as executor:
            futures = []

            for i, chunk in enumerate(chunks(pii_data, chunk_size)):
                future = executor.submit(hash_and_serialize_chunk,
                                         chunk, schema_types, keys)
                futures.append(future)

            for future in futures:
                results.extend(future.result())

    else:
        log.info("Hashing with one core, upgrade to python 3 to utilise all cores")

        results = hash_and_serialize_chunk(pii_data, schema_types, keys)

    log.info("Hashing took {:.2f} seconds".format(time.time() - start_time))
    return results


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]
