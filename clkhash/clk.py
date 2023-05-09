"""
Generate CLK from data.
"""

import concurrent.futures
import csv
import logging
import math
import multiprocessing
from itertools import islice, chain
from pathlib import Path
from typing import (AnyStr, Callable, cast, Iterable, List, Optional,
                    Sequence, Tuple, TypeVar, Union, Iterator)
from bitarray import bitarray
from tqdm import tqdm

from clkhash.bloomfilter import stream_bloom_filters
from clkhash.key_derivation import generate_key_lists
from clkhash.schema import Schema
from clkhash.stats import OnlineMeanVariance
from clkhash.validate_data import (validate_entries, validate_header,
                                   validate_row_lengths)

log = logging.getLogger('clkhash.clk')


def hash_chunk(chunk_pii_data: Sequence[Sequence[str]],
               keys: Sequence[Sequence[bytes]],
               schema: Schema,
               validate_data: bool,
               row_index_offset: int
               ) -> Tuple[List[bitarray], Sequence[int]]:
    """
    Generate Bloom filters (ie hash) from chunks of PII.
    It also computes and outputs the Hamming weight (or popcount) -- the number of bits
    set to one -- of the generated Bloom filters.

    :param chunk_pii_data: An iterable of indexable records.
    :param keys: A tuple of two lists of keys used in the HMAC. Should have been created by `generate_key_lists`.
    :param Schema schema: Schema specifying the entry formats and
            hashing settings.
    :param validate_data: validate pi data against format spec
    :return: A list of Bloom filters as bitarrays and a list of corresponding popcounts
    """
    validate_row_lengths(schema.fields, chunk_pii_data)
    if validate_data:
        validate_entries(schema.fields, chunk_pii_data, row_index_offset=row_index_offset)
    clk_data = []
    clk_popcounts = []
    for clk in stream_bloom_filters(chunk_pii_data, keys, schema):
        clk_data.append(clk[0])
        clk_popcounts.append(clk[2])
    return clk_data, clk_popcounts


def hash_chunk_from_queue(pii_chunks_queue: multiprocessing.Queue,
                          keys: Sequence[Sequence[bytes]],
                          schema: Schema,
                          validate_data: bool,
                          chunk_size: int
                          ) -> Tuple[List[bitarray], Sequence[int], int]:
    """
    Generate Bloom filters (ie hash) from chunks of PII.
    It also computes and outputs the Hamming weight (or popcount) -- the number of bits
    set to one -- of the generated Bloom filters.

    :param pii_chunks_queue: Queue that provides indexed chunks of pii.
    :param keys: A tuple of two lists of keys used in the HMAC. Should have been created by `generate_key_lists`.
    :param Schema schema: Schema specifying the entry formats and
            hashing settings.
    :param validate_data: validate pi data against format spec
    :return: A list of Bloom filters as bitarrays and a list of corresponding popcounts
    """
    chunk_idx, pi_chunk = pii_chunks_queue.get()
    clk_data, clk_popcounts = hash_chunk(pi_chunk, keys, schema, validate_data, chunk_idx + chunk_size)
    return clk_data, clk_popcounts, chunk_idx


def generate_clk_from_csv(filename: str,
                          secret: AnyStr,
                          schema: Schema,
                          validate: bool = True,
                          header: Union[bool, AnyStr] = True,
                          progress_bar: bool = True,
                          max_workers: Optional[int] = None
                          ) -> List[bitarray]:
    """ Generate Bloom filters for the records of a CSV file.

            This function also computes and outputs the Hamming weight
            (a.k.a popcount -- the number of bits set to high) of the
            generated Bloom filters.

            :param filename: The name of the file of csv data to hash.
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
            :return: A list of Bloom filters as bitarrays.
        """
    if header not in {False, True, 'ignore'}:
        raise ValueError("header must be False, True or 'ignore' but is {!s}."
                         .format(header))
    if not Path(filename).exists():
        raise ValueError(f"File {filename} does not exist.")

    record_count = line_count(filename) if header is False else line_count(filename) - 1

    if progress_bar:
        stats = OnlineMeanVariance()
        with tqdm(desc="generating CLKs", total=record_count, unit='clk', unit_scale=True,
                  postfix={'mean': stats.mean(), 'std': stats.std()}) as pbar:
            def callback(tics, clk_stats):
                stats.update(clk_stats)
                pbar.set_postfix(mean=stats.mean(), std=stats.std(), refresh=False)
                pbar.update(tics)

            results = generate_clks_from_csv_as_stream(filename,
                                                       record_count,
                                                       schema,
                                                       secret,
                                                       validate=validate,
                                                       callback=callback,
                                                       max_workers=max_workers
                                                       )
    else:
        results = generate_clks_from_csv_as_stream(filename,
                                                   record_count,
                                                   schema,
                                                   secret,
                                                   validate=validate,
                                                   header=header,
                                                   max_workers=max_workers
                                                   )
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

    # Chunks PII
    log.info(f"Hashing {len(pii_data)} entities")
    chunk_size = 200 if len(pii_data) <= 10_000 else 1000
    futures = []

    if max_workers is None or max_workers > 1:
        # Compute Bloom filter from the chunks and then serialise it
        with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
            for chunk_idx, chunk in chunks_gen(pii_data, chunk_size):
                future = executor.submit(
                    hash_chunk,
                    chunk, key_lists, schema, validate, chunk_idx * chunk_size)
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
        for chunk_idx, chunk in chunks_gen(pii_data, chunk_size):
            clks, clk_stats = hash_chunk(chunk, key_lists, schema, validate, chunk_idx * chunk_size)
            if callback is not None:
                unpacked_callback = cast(Callable[[int, Sequence[int]], None], callback)
                unpacked_callback(len(clks), clk_stats)
            results.extend(clks)
    return results


T = TypeVar('T')  # Declare generic type variable


def generate_clks_from_csv_as_stream(filename: str,
                                     record_count: int,
                                     schema: Schema,
                                     secret: AnyStr,
                                     validate: bool = True,
                                     header: Union[bool, AnyStr] = True,
                                     callback: Optional[Callable[[int, Sequence[int]], None]] = None,
                                     max_workers: Optional[int] = None
                                     ) -> List[bitarray]:

    if header not in {False, True, 'ignore'}:
        raise ValueError("header must be False, True or 'ignore' but is {!s}."
                         .format(header))
    if record_count + (1 if header else 0) == 0:
        raise ValueError(f"file {filename} does not contain any records.")

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

    # Chunks PII
    chunk_size = 10000
    num_chunks = math.ceil((record_count if not header else record_count - 1) / chunk_size)
    futures = []
    if num_chunks == 1:
        max_workers = 1

    if max_workers is None or max_workers > 1:

        with multiprocessing.Manager() as manager:
            queue_size = max_workers * 2 if max_workers is not None else multiprocessing.cpu_count() * 2
            chunks_queue = manager.Queue(queue_size)
            # create process that fills queue with chunks
            chunk_producer = multiprocessing.Process(target=produce_chunks, args=(chunks_queue, filename, chunk_size, header, schema))
            chunk_producer.start()

            # Compute Bloom filter from the chunks and then serialise it
            with concurrent.futures.ProcessPoolExecutor(max_workers=max_workers) as executor:
                for _ in range(num_chunks):
                    future = executor.submit(hash_chunk_from_queue, chunks_queue, key_lists, schema, validate, chunk_size)
                    if callback is not None:
                        unpacked_callback = cast(Callable[[int, Sequence[int]], None],
                                                 callback)
                        future.add_done_callback(
                            lambda f: unpacked_callback(len(f.result()[0]),
                                                        f.result()[1]))
                    futures.append(future)

                results = [[] for _ in range(num_chunks)]
                for future in futures:
                    clks, clk_stats, chunk_idx = future.result()
                    results[chunk_idx] = clks
                results = list(chain(*results))
    else:
        results = []
        with open(filename, 'rt') as f:
            reader = csv.reader(f)
            if header:
                column_names = next(reader)
                if header != 'ignore':
                    validate_header(schema.fields, column_names)
            for chunk_idx, chunk in chunks_gen(reader, chunk_size):
                clks, clk_stats = hash_chunk(chunk, key_lists, schema, validate, chunk_idx * chunk_size)
                if callback is not None:
                    unpacked_callback = cast(Callable[[int, Sequence[int]], None], callback)
                    unpacked_callback(len(clks), clk_stats)
                results.extend(clks)
    return results


def produce_chunks(queue, filename, chunk_size, header, schema):
    with open(filename, 'rt') as f:
        reader = csv.reader(f)
        if header:
            column_names = next(reader)
            if header != 'ignore':
                validate_header(schema.fields, column_names)

        for chunk_idx, pi_chunk in chunks_gen(reader, chunk_size):
            queue.put((chunk_idx, pi_chunk))


def chunks(seq: Sequence[T], chunk_size: int) -> Iterable[Sequence[T]]:
    """ Split seq into chunk_size-sized chunks.

        :param seq: A sequence to chunk.
        :param chunk_size: The size of chunk.
    """
    return (seq[i:i + chunk_size] for i in range(0, len(seq), chunk_size))


def chunks_gen(iterable: Iterable[T], chunk_size: int) -> Iterator[Tuple[int, Sequence[T]]]:
    """ Batch data into chunks of length chunk_size. The last chunk may be shorter.

        :param iterable: An iterable to chunk
        :param chunk_size: The size of a chunk.
    """
    if chunk_size < 1:
        raise ValueError('chunk_size must be at least one')
    it = iter(iterable)
    idx = 0
    while chunk := tuple(islice(it, chunk_size)):
        yield idx, chunk
        idx += 1


def line_count(filename: str) -> int:
    """ counts the number of lines in a textfile """

    def blocks(files, size=65536):
        while True:
            b = files.read(size)
            if not b:
                break
            yield b

    with open(filename, "r", encoding="utf-8", errors='ignore') as f:
        return sum(bl.count("\n") for bl in blocks(f))
