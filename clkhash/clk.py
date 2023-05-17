"""
Generate CLK from data.
"""
from __future__ import annotations
import concurrent.futures
import csv
import logging
import multiprocessing
from multiprocessing import Process, Queue
from itertools import islice
from threading import Thread
from typing import (AnyStr, Callable, cast, Iterable, List, Optional,
                    Sequence, Tuple, TypeVar, Union, Iterator, TextIO)
from bitarray import bitarray
from tqdm import tqdm

from clkhash.bloomfilter import stream_bloom_filters
from clkhash.concurent_helpers import queue_to_sorted_iterable
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
               #row_index_offset: int
               ) -> Tuple[List[bitarray], List[int]]:
    """
    Generate Bloom filters (ie hash) from chunks of PII.
    It also computes and outputs the Hamming weight (or popcount) -- the number of bits
    set to one -- of the generated Bloom filters.

    :param chunk_pii_data: An iterable of indexable records.
    :param keys: A tuple of two lists of keys used in the HMAC. Should have been created by `generate_key_lists`.
    :param Schema schema: Schema specifying the entry formats and
            hashing settings.
    :param validate_data: validate pi data against format spec
    :param row_index_offset: row index offset for reporting location
            of validation errors in provided data.
    :return: A list of Bloom filters as bitarrays and a list of corresponding popcounts
    """
    validate_row_lengths(schema.fields, chunk_pii_data)
    if validate_data:
        validate_entries(schema.fields, chunk_pii_data)
    clk_data = []
    clk_popcounts = []
    for clk in stream_bloom_filters(chunk_pii_data, keys, schema):
        clk_data.append(clk[0])
        clk_popcounts.append(clk[2])
    return clk_data, clk_popcounts


def iterable_to_queue(iterable: Iterable[Sequence], queue: Queue, num_workers):
    for item in iterable:
        queue.put(item)

    for _ in range(num_workers):
        queue.put(None)


def hash_chunk_from_queue(
        pii_chunk_queue: Queue[Sequence[Sequence[str]]],
        results_queue: Queue,
        keys: Sequence[Sequence[bytes]],
        schema: Schema,
        validate_data: bool,

    ) -> Tuple[List[bitarray], Sequence[int]]:
    """
    Generate Bloom filters (ie hash) from chunks of PII.
    It also computes and outputs the Hamming weight (or popcount) -- the number of bits
    set to one -- of the generated Bloom filters.

    :param pii_chunks_queue: Queue that provides indexed chunks of pii.
    :param results_queue: Queue that a list of Bloom filters as bitarrays and a list of corresponding popcounts
            will be added to on the completion of each chunk.
    :param keys: A tuple of two lists of keys used in the HMAC. Should have been created by `generate_key_lists`.
    :param Schema schema: Schema specifying the entry formats and
            hashing settings.
    :param validate_data: validate pi data against format spec

    """
    while chunk_info := pii_chunk_queue.get():
        if chunk_info is None:
            break
        chunk_index, chunk = chunk_info
        clk_data, clk_popcounts = hash_chunk(chunk, keys, schema, validate_data)
        results_queue.put((clk_data, clk_popcounts, chunk_index))

    results_queue.put(None)


def generate_clk_from_csv(input_f: TextIO,
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

    record_count = line_count(input_f)

    reader = csv.reader(input_f)
    if header:
        column_names = next(reader)
        if header != 'ignore':
            validate_header(schema.fields, column_names)


    if progress_bar:
        stats = OnlineMeanVariance()
        with tqdm(desc="generating CLKs", unit='clk', unit_scale=True,
                  postfix={'mean': stats.mean(), 'std': stats.std()}) as pbar:
            def callback(tics, clk_stats):
                stats.update(clk_stats)
                pbar.set_postfix(mean=stats.mean(), std=stats.std(), refresh=False)
                pbar.update(tics)

            results = generate_clks_from_csv_as_stream(reader,
                                                       record_count,
                                                       schema,
                                                       secret,
                                                       validate=validate,

                                                       callback=callback,
                                                       max_workers=max_workers
                                                       )
    else:
        results = generate_clks_from_csv_as_stream(reader,
                                                   record_count,
                                                   schema,
                                                   secret,
                                                   validate=validate,

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


def generate_clks_from_csv_as_stream(data: Iterable[Sequence[str]],
                                     record_count: int,
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

    # Chunk PII
    chunk_size = 10_000
    if record_count < chunk_size:
        max_workers = 1

    results: List = []
    if max_workers is None or max_workers > 1:
        max_workers = multiprocessing.cpu_count() if max_workers is None else max_workers
        # We put chunks of raw data into the queue
        queue = Queue(maxsize=1*max_workers)
        results_queue = Queue()

        # producer thread that consumes the iterable and puts chunk_size batches into a fixed size queue
        producer_thread = Thread(target=iterable_to_queue, args=(chunks_gen(data, chunk_size), queue, max_workers))
        producer_thread.start()

        consumers = []
        for _ in range(max_workers):
            p = Process(
                target=hash_chunk_from_queue,
                args=(queue, results_queue),
                kwargs={
                    'keys': key_lists,
                    'schema': schema,
                    'validate_data': validate,
                }
            )
            p.start()
            consumers.append(p)

        for result in queue_to_sorted_iterable(results_queue, max_workers):
            (clks, clk_stats, chunk_idx) = result

            if callback is not None:
                callback(len(clks), clk_stats)

            results.extend(clks)


    else:
        results = []

        for chunk_idx, chunk in chunks_gen(data, chunk_size):
            clks, clk_stats = hash_chunk(chunk, key_lists, schema, validate, chunk_idx * chunk_size)
            if callback is not None:
                unpacked_callback = cast(Callable[[int, Sequence[int]], None], callback)
                unpacked_callback(len(clks), clk_stats)
            results.extend(clks)
    return results


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


def line_count(file: TextIO) -> int:
    """ counts the number of lines in a textfile """

    def blocks(file: TextIO, size=65536):
        while True:
            b = file.read(size)
            if not b:
                break
            yield b


    count = sum(bl.count("\n") for bl in blocks(file))
    file.seek(0)
    return count
