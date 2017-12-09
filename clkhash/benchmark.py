from __future__ import print_function
from timeit import default_timer as timer
import tempfile
from clkhash.randomnames import NameList
from clkhash.schema import load_schema, get_schema_types
from clkhash.clk import generate_clk_from_csv


def compute_hash_speed(n, quiet=False):
    # type: (int, bool) -> float
    """
    Hash time.
    """
    namelist = NameList(n)

    tmpfile = tempfile.NamedTemporaryFile('wt')

    with open(tmpfile.name,'wt') as f:
        f.write("header row\n")
        for person in namelist.names:
            print(','.join([str(field) for field in person]), file=f)

    schema = get_schema_types(load_schema(None))

    with open(tmpfile.name, 'rt') as f:
        start = timer()
        generate_clk_from_csv(f, ('key1', 'key2'), schema, progress_bar=not quiet)
        end = timer()
    elapsed_time = end - start
    print("{:6d} hashes in {:.6f} seconds. {:.2f} KH/s".format(n, elapsed_time, n/(1000*elapsed_time)))
    return n / elapsed_time


if __name__ == '__main__':
    for n in [100, 1000, 10000, 50000, 100000]:
        compute_hash_speed(n)