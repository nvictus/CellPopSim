#-------------------------------------------------------------------------------
# Name:        channels
# Purpose:
#
# Author:      Nezar
#
# Created:     26/01/2012
# Copyright:   (c) Nezar 2012
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python
import heapq

#TODO: We may need to consider the case of equal priority values if
#      we wish to enforce an ordering on channels with equal event times.
class IndexedPriorityQueue(object):
    """
    Implements Indexed Priority Queue data structure as described in:
    Gibson and Bruck. J. Phys. Chem. A, Vol. 104, No. 9, 2000.

    Priority values and items are stored in a binary MIN-heap, implemented as a
    python list (heapq module). The constructor builds an initial heap. Entries
    can be added. Conceptually, entries are pairs of the form [item, key].
    Here, the highest priority item is the one with the *smallest* key.

    The class does not support popping single entries out. One can access the
    min entry but not remove it, and one can also update an existing entry's
    priority key or replace the item.

    """
    class Entry(object):
        def __init__(self, item, priority_key):
            self.priority_key = priority_key
            self.item = item

        def __lt__(self, other):
            return self.priority_key < other.priority_key

        def __gt__(self, other):
            return self.priority_key > other.priority_key

    def __init__(self, items, priorities):
        """
        Heapifies an array of tree nodes and creates the index structure.
        Each node stores an Entry object [priority, item].

        Args:
            items (list): items associated with a priority-determining key
            priorities (list): comparable values

        Notes:
            Index structure is a hash table mapping 'item' -> location of entry
            containing 'item' in the heap (i.e. node or index).
            WARNING: Each item must be unique!

        """
        self.heap = []
        for item, priority_key in zip(items, priorities):
            entry = IndexedPriorityQueue.Entry(item, priority_key)
            self.heap.append(entry)
        heapq.heapify(self.heap)

        # WARNING: Each item must be unique!!!
        self._index_of = {}
        i = 0;
        for entry in self.heap:
            self._index_of[entry.item] = i
            i += 1

    def peekMin(self):
        """
        Access the smallest entry.

        """
        min_entry = self.heap[0]
        return min_entry.priority_key, min_entry.item

    def add(self, item, priority_key):
        """
        Add a new entry while maintaining the heap invariant and the index
        structure.

        """
        entry = IndexedPriorityQueue.Entry(item, priority_key)
        index = len(self.heap)
        self.heap.append(entry)
        self._index_of[item] = index
        self._bubbleUp(index)

    def update(self, item, new_key):
        """
        Update an existing entry while maintaining the heap invariant and the
        index structure.

        """
        index = self._index_of[item]
        entry = self.heap[index]
        entry.priority_key = new_key
        self._updateReheapify(index)

    def replace(self, old_item, new_item, new_key=None):
        """
        Replace the item of an existing entry. Optionally, change the priority
        while maintaining the heap invariant and the index structure.

        """
        index = self._index_of[old_item]
        entry = self.heap[index]
        entry.item = new_item
        self._index_of[new_item] = index
        del self._index_of[old_item]
        if new_key is not None:
            entry.priority_key = new_key
            self._updateReheapify(index)

    def _swap(self, indexA, indexB):
        entryA = self.heap[indexA]
        entryB = self.heap[indexB]
        self.heap[indexA], self.heap[indexB] = entryB, entryA
        self._index_of[entryA.item] = indexB
        self._index_of[entryB.item] = indexA

    def _bubbleUp(self, index):
        parent_index = (index-1)//2
        while parent_index >= 0:
            entry = self.heap[index]
            parent = self.heap[parent_index]
            if entry < parent:
                self._swap(index, parent_index)
                index = parent_index
                parent_index = (index-1)//2
            else:
                break

    def _updateReheapify(self, index):
        # bubble up
        parent_index = (index-1)//2
        has_parent = parent_index >= 0
        while has_parent:
            entry = self.heap[index]
            parent = self.heap[parent_index]
            if entry < parent:
                self._swap(index, parent_index)
                index = parent_index
                parent_index = (index-1)//2
                has_parent = parent_index >= 0
            else:
                break

        # bubble down
        num_nodes = len(self.heap)-1
        l_child_index = 2*index+1
        r_child_index = 2*index+2
        has_child = l_child_index <= num_nodes
        while has_child:
            l_child = self.heap[l_child_index]
            try:
                r_child = self.heap[r_child_index]
            except(IndexError):
                min_child_index = l_child_index
            else:
                min_child_index = l_child_index if (l_child < r_child) else r_child_index
            min_child = self.heap[min_child_index]
            entry = self.heap[index]
            if entry > min_child:
                self._swap(index, min_child_index)
                index = min_child_index
                l_child_index = 2*index+1
                r_child_index = 2*index+2
                has_child = l_child_index <= num_nodes
            else:
                break

    def _printHeap(self):
        for entry in self.heap:
            print(entry.priority_key, entry.item)

    def _sortedKeys(self):
        h = self.heap[:]
        keys = []
        while h:
            keys.append(heapq.heappop(h).priority_key)
        return keys














# Some tests...
#-------------------------------------------------------------------------------
def _test_ipq():
    import random
    from event import AgentChannel

    # Test IPQ
    #----------
    priorities = []; items = []
    n = 50
    m = 10
    for i in range(0,n):
        priorities.append(random.uniform(0,m))
        items.append(AgentChannel())

    pq = IndexedPriorityQueue(items, priorities)

    pq.update(items[random.randint(0,n-1)], random.uniform(0,m))
    pq.update(items[random.randint(0,n-1)], random.uniform(0,m))
    pq.update(items[random.randint(0,n-1)], random.randint(0,m))
    pq.update(items[random.randint(0,n-1)], random.randint(0,m))
    pq.update(items[random.randint(0,n-1)], random.randint(0,m))

    for entry in pq.heap:
        print(entry.priority_key)
    print()

    t = pq._sortedKeys()
    for elem in t:
        print(elem)
    assert(t == sorted(t))

if __name__ == '__main__':
    _test_ipq()
