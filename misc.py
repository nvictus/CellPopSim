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

from base import *
import heapq

class AgentQueue(object):
    """
    Holds a list of agents sorted by birth time.

    Attributes:
        heap (list): binary heap holding parent and child agents

    """
    def __init__(self):
        self.heap = []

    def addAgent(self, parent, child):
        heapq.heappush(self.heap, (parent._engine.clock, parent, child))

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


import math
import random

class GillespieChannel(AgentChannel):
    """ Performs Gillespie SSA """
    def __init__(self, propensity_fcn, stoich_list):
        self.propensity_fcn = propensity_fcn
        self.stoich_list = stoich_list
        self.tau = None
        self.mu = None

    def scheduleEvent(self, cell, gdata, time, source):
        a = self.propensity_fcn(cell.state.x, gdata.state)
        a0 = sum(a)
        self.tau = -math.log(random.uniform(0,1))/a0
        s = a[0]
        self.mu = 0
        r0 = random.uniform(0,1)*a0
        while s <= r0:
            self.mu += 1
            s += a[self.mu]
        return time + self.tau

    def fireEvent(self, cell, gdata, time, event_time, aq, rq):
        for i in range(0, len(cell.state.x)):
            cell.state.x[i] += self.stoich_list[self.mu][i]
            if cell.state.x < [0, 0]:
                raise Exception
        return True

def main2():
    s = ((1, 0), (0, 1), (-1, 0), (0, -1))
    prop_fcn = lambda x, p: [ p.kR, p.kP*x[0], p.gR*x[0], p.gP*x[1] ]
    channel = GillespieChannel(propensity_fcn=prop_fcn, stoich_list=s)

    cell = Agent(State( ('x',) ), None)
    cell.state.x = [0, 0]
    gdata = World(State( ('kR','kP','gR','gP') ), None)
    gdata.state.kR = 0.1
    gdata.state.kP = 0.1
    gdata.state.gR = 0.1
    gdata.state.gP = 0.002

    tstop = 100
    t = [0.0]
    x = [tuple(cell.state.x)]
    while t[-1] < tstop:
        ev_time = channel.scheduleEvent(cell, gdata, t[-1], None)
        is_mod = channel.fireEvent(cell, gdata, t[-1], ev_time, [], [])
        t.append(ev_time)
        x.append(tuple(cell.state.x))
    for i in range(len(x)):
        print(t[i],'\t',x[i])


if __name__ == '__main__':
    main()
