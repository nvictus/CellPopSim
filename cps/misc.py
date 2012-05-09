"""
Name:        misc

Author:      Nezar Abdennur <nabdennur@gmail.com>
Created:     26/01/2012
Copyright:   (c) Nezar Abdennur 2012

"""
#!/usr/bin/env python

import collections

class IPQEntry(object):
    def __init__(self, item, pkey):
        self.item = item
        self.pkey = pkey

    def __lt__(self, other):
        return self.pkey < other.pkey

    def __eq__(self, other):
        return self.pkey == other.pkey

    def __repr__(self):
        return "PQDEntry(" + str(self.item) + ": " + str(self.pkey) + ")"

#TODO: We may need to consider the case of equal priority values if
#      we wish to enforce an ordering on channels with equal event times.

# One option is to override __lt__ for tie-breaking rules.
#
# We could also use tuples/lists for comparison [priority_key, ordering_index]
# where each item gets a unique ordering index (e.g. pre-specified or based on
# when it is inserted). Python sequence comparison will automatically use the
# second element when the first compares equal.


class IndexedPriorityQueue(collections.MutableMapping):
    """
    Implements Indexed Priority Queue data structure as described in:
    Gibson and Bruck. J. Phys. Chem. A, Vol. 104, No. 9, 2000.

    Priority values and items are stored in a binary MIN-heap, implemented as a
    python list. The constructor builds an initial heap. Entries can be added.
    Conceptually, entries are pairs of the form [item, key]. Here, the highest
    priority item is the one with the *smallest* key.

    """
    __slots__ = ('heap', 'nodefinder','cmp')

    def __init__(self, *args):
        self.heap = []
        self.nodefinder = {}
        self.cmp = IPQEntry
        if args:
            d = dict(*args)
            for dkey, pkey in d.items():
                self[dkey] = pkey
            self._heapify()

    def __len__(self):
        """
        Return number of items in the PQD.

        """
        return len(self.nodefinder)

    def __contains__(self, dkey):
        """
        Return True if dkey is in the PQD else return False.

        """
        return dkey in self.nodefinder

    def __iter__(self):
        """
        Return an iterator over the keys of the PQD.

        """
        return self.nodefinder.__iter__()

    def __getitem__(self, dkey):
        """
        Return the priority of dkey. Raises a KeyError if not in the PQD.

        """
        return self.heap[self.nodefinder[dkey]].pkey #raises KeyError

    def __setitem__(self, dkey, pkey):
        """
        Set priority key of item dkey.

        """
        heap = self.heap
        finder = self.nodefinder
        try:
            pos = finder[dkey]
        except KeyError:
            # add new entry
            n = len(self.heap)
            self.heap.append(self.cmp(dkey, pkey))
            self.nodefinder[dkey] = n
            self._swim(n)
        else:
            # update existing entry
            heap[pos].pkey = pkey
            parent_pos = (pos - 1) >> 1
            child_pos = 2*pos + 1
            if parent_pos > 0 and heap[pos] < heap[parent_pos]:
                self._swim(pos)
            elif child_pos < len(heap):
                right_pos = child_pos + 1
                if right_pos < len(heap) and not heap[child_pos] < heap[right_pos]:
                    child_pos = right_pos
                if heap[child_pos] < heap[pos]:
                    self._sink(pos)

    def __delitem__(self, dkey):
        """
        Remove item dkey. Raises a KeyError if dkey is not in the PQD.

        """
        heap = self.heap
        finder = self.nodefinder

        # Remove very last item and place in vacant spot. Let the new item
        # sink until it reaches its new resting place.
        try:
            pos = finder.pop(dkey)
        except KeyError:
            raise
        else:
            entry = heap[pos]
            last = heap.pop(-1)
            if entry is not last:
                heap[pos] = last
                finder[last.item] = pos
                parent_pos = (pos - 1) >> 1
                child_pos = 2*pos + 1
                if parent_pos > 0 and heap[pos] < heap[parent_pos]:
                    self._swim(pos)
                elif child_pos < len(heap):
                    right_pos = child_pos + 1
                    if right_pos < len(heap) and not heap[child_pos] < heap[right_pos]:
                        child_pos = right_pos
                    if heap[child_pos] < heap[pos]:
                        self._sink(pos)
            del entry

    def __copy__(self):
        """
        Return a new PQD with the same dkeys (shallow copied) and priority keys.

        """
        #TODO: deep copy priority keys? shouldn't these always be int/float anyway?
        from copy import copy
        other = PriorityQueueDict()
        other.heap = [copy(entry) for entry in self.heap]
        other.nodefinder = copy(self.nodefinder)
        return other

    copy = __copy__
    __eq__ = collections.MutableMapping.__eq__
    __ne__ = collections.MutableMapping.__ne__
    get = collections.MutableMapping.get
    keys = collections.MutableMapping.keys
    values = collections.MutableMapping.values
    items = collections.MutableMapping.items
    clear = collections.MutableMapping.clear
    setdefault = collections.MutableMapping.setdefault
    __marker = object()

    def pop(self, dkey, default=__marker):
        """
        If key is in the PQD, remove it and return its priority key, else return
        default. If default is not given and dkey is not in the PQD, a KeyError
        is raised.

        """
        heap = self.heap
        finder = self.nodefinder

        try:
            pos = finder.pop(dkey)
        except KeyError:
            if default is self.__marker:
                raise
            return default
        else:
            delentry = heap[pos]
            last = heap.pop(-1)
            if delentry is not last:
                heap[pos] = last
                finder[last.item] = pos
                parent_pos = (pos - 1) >> 1
                child_pos = 2*pos + 1
                if parent_pos > 0 and heap[pos] < heap[parent_pos]:
                    self._swim(pos)
                elif child_pos < len(heap):
                    right_pos = child_pos + 1
                    if right_pos < len(heap) and not heap[child_pos] < heap[right_pos]:
                        child_pos = right_pos
                    if heap[child_pos] < heap[pos]:
                        self._sink(pos)
            pkey = delentry.pkey
            del delentry
            return pkey

    def popitem(self):
        """
        Extract top priority item. Raises KeyError if PQD is empty.

        """
        try:
            last = self.heap.pop(-1)
        except IndexError:
            raise KeyError
        else:
            if self.heap:
                entry = self.heap[0]
                self.heap[0] = last
                self.nodefinder[last.item] = 0
                self._sink(0)
            else:
                entry = last
            self.nodefinder.pop(entry.item)
            return entry.item, entry.pkey

    def add(self, dkey, pkey):
        """
        Add a new item. Raises KeyError if item is already in the PQD.

        """
        if dkey in self.nodefinder:
            raise KeyError
        self[dkey] = pkey

    def updateitem(self, dkey, new_pkey):
        """
        Update the priority key of an existing item. Raises KeyError if item is
        not in the PQD.

        """
        if dkey not in self.nodefinder:
            raise KeyError
        self[dkey] = new_pkey

    def replaceitem(self, old_item, new_item, new_pkey=None):
        """
        Replace the item of an existing entry. Optionally, change the priority
        while maintaining the heap invariant and the index structure.

        """
        if old_item not in self.nodefinder:
            raise KeyError
        pos = self.nodefinder[old_item]
        entry = self.heap[pos]
        entry.item = new_item
        self.nodefinder[new_item] = pos
        del self.nodefinder[old_item]
        if new_pkey is not None:
            self[new_item] = new_pkey

    def peek(self):
        """
        Get top priority item.

        """
        try:
            entry = self.heap[0]
        except IndexError:
            raise KeyError
        return entry.item, entry.pkey

    def _heapify(self):
        n = len(self.heap)
        for pos in reversed(range(n//2)):
            self._sink(pos)

    def _sink(self, top=0):
        heap = self.heap
        finder = self.nodefinder

        # Peel off top item
        pos = top
        entry = heap[pos]

        # Sift up a trail of child nodes
        child_pos = 2*pos + 1
        while child_pos < len(heap):
            # Choose the index of smaller child.
            right_pos = child_pos + 1
            if right_pos < len(heap) and not heap[child_pos] < heap[right_pos]:
                child_pos = right_pos

            # Move the smaller child up.
            child_entry = heap[child_pos]
            heap[pos] = child_entry
            finder[child_entry.item] = pos

            pos = child_pos
            child_pos = 2*pos + 1

        # We are now at a leaf. Put item there and let it swim until it reaches
        # its new resting place.
        heap[pos] = entry
        finder[entry.item] = pos
        self._swim(pos, top)

    def _swim(self, pos, top=0):
        heap = self.heap
        finder = self.nodefinder

        # Remove item from its place
        entry = heap[pos]

        # Bubble item up by sifting parents down until finding a place it fits.
        while pos > top:
            parent_pos = (pos - 1) >> 1
            parent_entry = heap[parent_pos]
            if entry < parent_entry:
                heap[pos] = parent_entry
                finder[parent_entry.item] = pos
                pos = parent_pos
                continue
            break

        # Put item in its new place
        heap[pos] = entry
        finder[entry.item] = pos








# Some tests...
#-------------------------------------------------------------------------------
def _test_ipq():
    import random
    from cps.channel import AgentChannel

    # Test IPQ
    #----------
    priorities = []; items = []
    n = 50
    m = 10
    for i in range(0,n):
        priorities.append(random.uniform(0,m))
        items.append(AgentChannel())

    pq = IndexedPriorityQueue(zip(items, priorities))

    pq.updateitem(items[random.randint(0,n-1)], random.uniform(0,m))
    pq.updateitem(items[random.randint(0,n-1)], random.uniform(0,m))
    pq.updateitem(items[random.randint(0,n-1)], random.randint(0,m))
    pq.updateitem(items[random.randint(0,n-1)], random.randint(0,m))
    pq.updateitem(items[random.randint(0,n-1)], random.randint(0,m))

    for entry in pq.heap:
        print(entry.pkey)
    print()

##    t = pq._sortedKeys()
##    for elem in t:
##        print(elem)
##    assert(t == sorted(t))

if __name__ == '__main__':
    _test_ipq()
