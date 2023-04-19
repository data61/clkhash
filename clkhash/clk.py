"""
Generate CLK from data.
"""

import concurrent.futures
import csv
import logging
import time
from typing import (AnyStr, Callable, cast, Iterable, List, Optional,
                    Sequence, TextIO, Tuple, TypeVar, Union)
from bitarray import bitarray
from tqdm import tqdm

from clkhash.bloomfilter import stream_bloom_filters
from clkhash.serialization import serialize_bitarray
from clkhash.key_derivation import generate_key_lists
from clkhash.schema import Schema
from clkhash.stats import OnlineMeanVariance
from clkhash.validate_data import (validate_entries, validate_header,
                                   validate_row_lengths)

log = logging.getLogger('clkhash.clk')



def hash_chunk(chunk_pii_data: Sequence[Sequence[str]],
               keys: Sequence[Sequence[bytes]],
               schema: Schema
               ) -> Tuple[List[bitarray], Sequence[int]]:
    """
    Generate Bloom filters (ie hash) from chunks of PII.
    It also computes and outputs the Hamming weight (or popcount) -- the number of bits
    set to one -- of the generated Bloom filters.

    :param chunk_pii_data: An iterable of indexable records.
    :param keys: A tuple of two lists of keys used in the HMAC. Should have been created by `generate_key_lists`.
    :param Schema schema: Schema specifying the entry formats and
            hashing settings.
    :return: A list of Bloom filters as bitarrays and a list of corresponding popcounts
    """
    clk_data = []
    clk_popcounts = []
    for clk in stream_bloom_filters(chunk_pii_data, keys, schema):
        clk_data.append(clk[0])
        clk_popcounts.append(clk[2])
    return clk_data, clk_popcounts


def generate_clk_from_csv(input_f: TextIO,
                          secret: AnyStr,
                          schema: Schema,
                          validate: bool = True,
                          header: Union[bool, AnyStr] = True,
                          progress_bar: bool = True,
                          max_workers: Optional[int] = None
                          ) -> List[bitarray]:
    """ Generate Bloom filters from CSV file, then serialise them.

        This function also computes and outputs the Hamming weight
        (a.k.a popcount -- the number of bits set to high) of the
        generated Bloom filters.

        :param input_f: A file-like object of csv data to hash.
        :param secret: A secret.
        :param schema: Schema specifying the record formats and
            hashing settings.
        :param validate: Set to `False` to disable validation of
            data against the schema. Note that this will silence
            warnings whose aim is to keep the hashes consistent between
            data sources; this may affect linkage accuracy.
        :param header: Set to `False` if the CSV file does not have
            a header. Set to `'ignore'` if the CSV file does have a
            header but it should not be checked against the schema.
        :param bool progress_bar: Set to `False` to disable the progress
            bar.
        :param int max_workers: Passed to ProcessPoolExecutor except for the
            special case where the value is 1, in which case no processes
            or threads are used. This may be useful or required on platforms
            that are not capable of spawning subprocesses.
        :return: A list of Bloom filters as bitarrays and a list of
            corresponding popcounts.
    """
    if header not in {False, True, 'ignore'}:
        raise ValueError("header must be False, True or 'ignore' but is {!s}."
                         .format(header))

    log.info("Hashing data")

    # Read from CSV file
    reader = csv.reader(input_f)

    if header:
        column_names = next(reader)
        if header != 'ignore':
            validate_header(schema.fields, column_names)

    start_time = time.time()

    # Read the lines in CSV file and add it to PII
    pii_data = []
    for line in reader:
        pii_data.append(tuple(element.strip() for element in line))

    validate_row_lengths(schema.fields, pii_data)

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
                                    secret,
                                    validate=validate,
                                    callback=callback,
                                    max_workers=max_workers
                                    )
    else:
        results = generate_clks(pii_data,
                                schema,
                                secret,
                                validate=validate,
                                max_workers=max_workers
                                )

    log.info(f"Hashing took {time.time() - start_time:.2f} seconds")
    return results


def generate_clks(pii_data: Sequence[Sequence[str]],
                  schema: Schema,
                  secret: AnyStr,
                  validate: bool = True,
                  callback: Optional[Callable[[int, Sequence[int]], None]] = None,
                  max_workers: Optional[int] = None
                  ) -> List[bitarray]:


    # Generate two keys for each identifier from the secret, one key per hashing method used when computing
    # the bloom filters.
    # Otherwise, it could create more if required using the parameter `num_hashing_methods` in `generate_key_lists`
    key_lists = generate_key_lists(
        secret,
        len(schema.fields),
        key_size=schema.kdf_key_size,
        salt=schema.kdf_salt,
        info=schema.kdf_info,
        kdf=schema.kdf_type,
        hash_algo=schema.kdf_hash)

    if validate:
        validate_entries(schema.fields, pii_data)

    # Chunks PII
    log.info(f"Hashing {len(pii_data)} entities")
    chunk_size = 200 if len(pii_data) <= 10_000 else 1000
    futures = []

    if max_workers is None or max_workers > 1:
        # Compute Bloom filter from the chunks and then serialise it
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            for chunk in chunks(pii_data, chunk_size):
                future = executor.submit(
                    hash_chunk,
                    chunk, key_lists, schema, )
                if callback is not None:
                    unpacked_callback = cast(Callable[[int, Sequence[int]], None],
                                             callback)
                    future.add_done_callback(
                        lambda f: unpacked_callback(len(f.result()[0]),
                                                    f.result()[1]))
                futures.append(future)

            results = []
            for future in futures:
                clks, clk_stats = future.result()
                results.extend(clks)
    else:
        results = []
        for chunk in chunks(pii_data, chunk_size):
            clks, clk_stats = hash_chunk(chunk, key_lists, schema)
            if callback is not None:
                unpacked_callback = cast(Callable[[int, Sequence[int]], None], callback)
                unpacked_callback(len(clks), clk_stats)
            results.extend(clks)
    return results


T = TypeVar('T')  # Declare generic type variable


def chunks(seq: Sequence[T], chunk_size: int) -> Iterable[Sequence[T]]:
    """ Split seq into chunk_size-sized chunks.

        :param seq: A sequence to chunk.
        :param chunk_size: The size of chunk.
    """
    return (seq[i:i + chunk_size] for i in range(0, len(seq), chunk_size))
