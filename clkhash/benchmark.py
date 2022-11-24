import os
import tempfile
from timeit import default_timer as timer

from clkhash.clk import generate_clk_from_csv
from clkhash.randomnames import NameList


def compute_hash_speed(num: int, quiet: bool = False, max_workers=None) -> float:
    """ Hash time.
    """
    namelist = NameList(num)
    os_fd, tmpfile_name = tempfile.mkstemp(text=True)

    schema = NameList.SCHEMA
    header_row = ','.join([f.identifier for f in schema.fields])

    with open(tmpfile_name, 'w') as f:
        f.write(header_row)
        f.write('\n')
        for person in namelist.names:
            print(','.join([str(field) for field in person]), file=f)

    with open(tmpfile_name) as f:
        start = timer()
        generate_clk_from_csv(f, 'secret', schema, progress_bar=not quiet, max_workers=max_workers)
        end = timer()

    os.close(os_fd)
    os.remove(tmpfile_name)

    elapsed_time = end - start
    if not quiet:
        print(f"{num:6d} hashes in {elapsed_time:.6f} seconds. {num / (1000 * elapsed_time):.2f} KH/s")
    return num / elapsed_time


if __name__ == '__main__':
    for max_workers in [1, 2, 4, 8, 16]:
        print()
        if max_workers == 1:
            print("Without multiprocessing")
            sizes = [10_000]
        else:
            print(f"Using up to {max_workers} workers")
            sizes = [10_000, 50_000, 100_000]

        for n in sizes:
            compute_hash_speed(n, max_workers=max_workers)
