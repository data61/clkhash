from __future__ import annotations

import heapq
from multiprocessing import Queue
from typing import Iterator, Tuple, List, TypeVar, Optional

A = TypeVar('A')
B = TypeVar('B')
ENCODED_CHUNK = Tuple[A, B, int]

def queue_to_sorted_iterable(queue: Queue[Optional[ENCODED_CHUNK]], sentinel_count: int) -> Iterator[ENCODED_CHUNK]:
    """
    Consume items from a multiprocessing Queue and yield them in order of their index.

    Items consumed from the queue are expected to be either `None` (a sentinel value indicating
    that a producer has finished) or a tuple `(_, _, index)`. The function will continue consuming
    items from the queue until it has received `sentinel_count` sentinel values, at which point it
    will assume that all producers have finished and no more items will be added to the queue.

    The function maintains a heap (priority queue) to keep track of out-of-order items. As items
    are consumed from the queue, they are added to the heap until the function finds the next item
    in order (i.e., an item with an index equal to the current count of yielded items). The function
    then yields all available items in order, removes them from the heap, and repeats the process.

    This approach allows the function to yield items in order as soon as possible, while keeping
    memory usage as low as possible by only storing out-of-order items.
    """
    # keep the out of order items from the queue in a heap
    heap: List[Tuple[int, ENCODED_CHUNK]] = []
    next_index = 0
    seen_sentinels = 0
    while seen_sentinels < sentinel_count:
        while True:  # Keep adding items to heap until we get the next item in order
            item = queue.get()
            if item is None:  # End sentinel
                seen_sentinels += 1
                if seen_sentinels == sentinel_count:
                    break
            else:
                # heapq uses the first element of the tuple for sorting
                # So, we add index as the first element
                heapq.heappush(heap, (item[2], item))
                if heap[0][0] == next_index:  # The next item in order is at the top of the heap
                    break
        else:  # If all the sentinels were found
            break

        while heap and heap[0][0] == next_index:  # Yield all available items in order
            _, item = heapq.heappop(heap)
            yield item
            next_index += 1

        # Yield any remaining items in order
    while heap:
        _, item = heapq.heappop(heap)
        yield item
