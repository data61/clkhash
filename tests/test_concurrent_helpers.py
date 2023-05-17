import unittest
from queue import Queue
from hypothesis import given, strategies as st

from clkhash.concurent_helpers import queue_to_sorted_iterable


class TestQueueToSortedIterable(unittest.TestCase):

    def test_queue_to_sorted_iterable_no_items(self):
        """
        Test that the function works correctly with an empty queue.
        """
        queue = Queue()
        sentinel_count = 1
        queue.put(None)  # End sentinel
        result = list(queue_to_sorted_iterable(queue, sentinel_count))
        self.assertEqual(result, [])

    @given(st.lists(st.tuples(st.integers(), st.integers(), st.integers(min_value=0)),
           min_size=1, unique_by=lambda x: x[2]))
    def test_queue_to_sorted_iterable_multiple_items(self, items):
        """
        Test that the function works correctly with a queue that contains multiple items.
        """
        queue = Queue()
        sentinel_count = 1

        # Put items in queue
        for item in items:
            queue.put(item)
        queue.put(None)  # End sentinel

        # Sort items by index
        items.sort(key=lambda x: x[2])

        result = list(queue_to_sorted_iterable(queue, sentinel_count))
        self.assertEqual(result, items)

    @given(st.lists(st.tuples(st.integers(), st.integers(), st.integers(min_value=0)),
                    min_size=1, unique_by=lambda x: x[2]))
    def test_queue_to_sorted_iterable_multiple_producers(self, items):
        """
        Test that the function works correctly with a queue that has items from multiple producers.
        """
        queue = Queue()
        sentinel_count = 2  # Assume we have 2 producers

        # Split items into two roughly equal groups, simulating two producers
        mid = len(items) // 2
        items1 = items[:mid]
        items2 = items[mid:]

        # Sort items within each group by index
        items1.sort(key=lambda x: x[2])
        items2.sort(key=lambda x: x[2])

        # Put items from each group in queue
        for item in items1:
            queue.put(item)
        queue.put(None)  # End sentinel for producer 1

        for item in items2:
            queue.put(item)
        queue.put(None)  # End sentinel for producer 2

        # Sort all items by index
        items.sort(key=lambda x: x[2])

        result = list(queue_to_sorted_iterable(queue, sentinel_count))
        self.assertEqual(result, items)

    @given(st.lists(st.tuples(st.integers(), st.integers(), st.integers(min_value=0)),
                    min_size=1, unique_by=lambda x: x[2]))
    def test_queue_to_sorted_iterable_multiple_sentinels(self, items):
        """
        Test that the function works correctly with a queue that contains multiple sentinel values.
        """
        queue = Queue()
        sentinel_count = 3  # Assume we have 3 producers

        # Split items into three roughly equal groups, simulating three producers
        one_third = len(items) // 3
        items1 = items[:one_third]
        items2 = items[one_third:2*one_third]
        items3 = items[2*one_third:]

        # Sort items within each group by index
        items1.sort(key=lambda x: x[2])
        items2.sort(key=lambda x: x[2])
        items3.sort(key=lambda x: x[2])

        # Put items from each group in queue
        for item in items1:
            queue.put(item)
        queue.put(None)  # End sentinel for producer 1

        for item in items2:
            queue.put(item)
        queue.put(None)  # End sentinel for producer 2

        for item in items3:
            queue.put(item)
        queue.put(None)  # End sentinel for producer 3

        # Sort all items by index
        items.sort(key=lambda x: x[2])

        result = list(queue_to_sorted_iterable(queue, sentinel_count))
        self.assertEqual(result, items)

    @given(st.lists(st.tuples(st.integers(), st.integers(), st.integers(min_value=0)),
           min_size=1, unique_by=lambda x: x[2]))
    def test_queue_to_sorted_iterable_multiple_items_in_order(self, items):
        """
        Test that the function maintains the order of items that are already sorted.
        """
        queue = Queue()
        sentinel_count = 1  # Assume we have 1 producer

        # Sort items by index to ensure they are in order
        items.sort(key=lambda x: x[2])

        # Put items in queue
        for item in items:
            queue.put(item)
        queue.put(None)  # End sentinel

        result = list(queue_to_sorted_iterable(queue, sentinel_count))
        self.assertEqual(result, items)

    @given(st.lists(st.tuples(st.integers(), st.integers(), st.integers(min_value=0)),
                    min_size=1, unique_by=lambda x: x[2]),
           st.integers(min_value=1, max_value=3))
    def test_queue_to_sorted_iterable_sentinel_count(self, items, sentinel_count):
        """
        Test that the function stops consuming from the queue when it has received the specified number of sentinel values.
        """
        queue = Queue()

        # Split items into groups, each group representing a producer
        split_points = [len(items)*i//sentinel_count for i in range(sentinel_count)]
        split_points.append(len(items))
        item_groups = [items[split_points[i]:split_points[i+1]] for i in range(sentinel_count)]

        # Sort items within each group by index
        for item_group in item_groups:
            item_group.sort(key=lambda x: x[2])

        # Put items from each group in queue
        for item_group in item_groups:
            for item in item_group:
                queue.put(item)
            queue.put(None)  # End sentinel for each producer

        # Sort all items by index
        items.sort(key=lambda x: x[2])

        result = list(queue_to_sorted_iterable(queue, sentinel_count))
        self.assertEqual(result, items)


