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

class LineageNode(object):
    """
    Keep a log of events over an agent's lifetime.

    """
    def __init__(self, parent=None):
        self.parent = parent
        self.lchild = None
        self.rchild = None
        self.log = []

    def record(self, time_stamp, channel_id, state):
        self.log.append( (time_stamp, channel_id) ) #TODO: log state values

    def split(self):
        l_node = LineageNode(parent=self)
        self.lchild = l_node
        r_node = LineageNode(parent=self)
        self.rchild = r_node
        return l_node, r_node


class AgentQueue(object):
    """
    Holds a list of agents sorted by birth time.

    Attributes:
        heap (list): binary heap holding parent and child agents

    """
    def __init__(self):
        self.heap = []

    def addAgent(self, parent, child, div_time):
        heapq.heappush(self.heap, (div_time, parent, child))

    def popAgent(self):
        div_time, parent, child = heapq.heappop(self.heap)
        return parent, child

    def isEmpty(self):
        return len(self.heap) == 0



#TODO: We may need to consider the case of equal priority values if
#      we wish to enforce an ordering on channels with equal event times.
class IndexedPriorityQueue(object):
    """
    Implements Indexed Priority Queue data structure as described in:
    Gibson and Bruck. J. Phys. Chem. A, Vol. 104, No. 9, 2000.

    Priority values and items are stored in a binary MIN-heap, implemented as a
    python list (array). The constructor builds an initial heap. Entries can be
    added. Conceptually, entries are pairs of the form [item, value]. Here,
    the highest priority item is the one with the *smallest* value.

    The class does not support popping single entries out, not even the top
    priority entry. One can update a given entry's priority or replace its item,
    and one can access the min entry but cannot remove it.

    """

    class Entry(object):
        def __init__(self, item, value):
            self.item = item
            self.value = value

        def __lt__(self, other):
            return self.value < other.value

        def __gt__(self, other):
            return self.value > other.value

    def __init__(self, items, values):
        """
        Heapifies an array of tree nodes and creates the index structure.
        Each node stores an Entry object [item, value].

        Args:
            items (list): items associated with a priority-determining value
            values (list): comparable values

        Notes:
            Index structure is a hash table mapping 'item' -> location of entry
            containing 'item' in the heap (i.e. node or index).
            WARNING: Each item must be unique!

        """
        self.heap = []
        for item, value in zip(items, values):
            entry = IndexedPriorityQueue.Entry(item, value)
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
        return min_entry.value, min_entry.item

    def add(self, item, value):
        """
        Add a new entry while maintaining the heap invariant and the index
        structure.

        """
        entry = IndexedPriorityQueue.Entry(item, value)
        index = len(self.heap)
        self.heap.append(entry)
        self._index_of[item] = index
        self._bubbleUp(index)

    def update(self, item, new_value):
        """
        Update an existing entry while maintaining the heap invariant and the
        index structure.

        """
        index = self._index_of[item]
        entry = self.heap[index]
        entry.value = new_value
        self._updateReheapify(index)

    def replace(self, old_item, new_item, value=None):
        """
        Replace the item of an existing entry. Optionally, change the priority
        while maintaining the heap invariant and the index structure.

        """
        index = self._index_of[old_item]
        entry = self.heap[index]
        entry.item = new_item
        self._index_of[new_item] = index
        del self._index_of[old_item]
        if value is not None:
            entry.value = value
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
            print(entry.value, entry.item)

    def _sortedValues(self):
        h = self.heap[:]
        values = []
        while h:
            values.append(heapq.heappop(h).value)
        return values














# Some tests...
#-------------------------------------------------------------------------------
#import unittest
import random

def main():
    p = []; c = []
    n = 50
    m = 10
    for i in range(0,n):
        p.append(random.uniform(0,m))
        c.append(Channel())

    pq = IndexedPriorityQueue(c, p)

    pq.update(c[random.randint(0,n)], random.uniform(0,m))
    pq.update(c[random.randint(0,n)], random.uniform(0,m))
    pq.update(c[random.randint(0,n)], random.randint(0,m))
    pq.update(c[random.randint(0,n)], random.randint(0,m))
    pq.update(c[random.randint(0,n)], random.randint(0,m))

    for entry in pq.heap: print(entry.value)
    print()

    t = pq.sortedValues()
    for elem in t: print(elem)
    assert(t == sorted(t))

    print()


#-------------------------------------------------------------------------------
if __name__ == '__main__':
    main()
