from timeit import default_timer as timer

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

