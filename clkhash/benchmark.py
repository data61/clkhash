from timeit import default_timer as timer
import tempfile
from clkhash.bloomhash import hash_csv
from clkhash.randomnames import NameList
from clkhash.schema import load_schema, get_schema_types
from clkhash.util import popcount_vector, generate_clks, generate_bitarray


some_filters = generate_clks(10000)


def compute_popcount_speed(n):
    """
    Just do as much counting of bits.
    """
    clks = [generate_bitarray(1024) for _ in range(n)]
    start = timer()
    popcounts = popcount_vector(clks)
    end = timer()
    elapsed_time = end - start
    print("{:6d} x 1024 bit popcounts in {:.6f} seconds".format(n, elapsed_time))
    speed_in_MiB = n / (1024 * 8 * elapsed_time)
    print("Popcount speed: {:.2f} MiB/s".format(speed_in_MiB))
    return speed_in_MiB


def compute_hash_speed(n):
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
        hash_csv(f, ('key1', 'key2'), schema)
        end = timer()
    elapsed_time = end - start
    print("{:6d} hashes in {:.6f} seconds".format(n, elapsed_time))


if __name__ == '__main__':
    compute_hash_speed(1000)