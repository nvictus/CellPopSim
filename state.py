#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      Nezar
#
# Created:     23/04/2012
# Copyright:   (c) Nezar 2012
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python
import numpy as np
import h5py
from copy import copy, deepcopy


def default_logger(state):
    return [copy(getattr(state,name)) for name in state._names]

class State(object):
    """
    Contain the state variables of an entity.

    """
    def __init__(self, var_names, logger=default_logger):
        self._do_log = logger
        self._names = []
        for name in var_names:
            setattr(self, name, None)
            self._names.append(name)

    def __copy__(self):
        new_state = State(self._names, self._do_log)
        for name in self._names:
            setattr(new_state, name, copy(getattr(self, name)))
        return new_state

    def snapshot(self):
        return self._do_log(self)


def _traversal(node, order=-1, adj_list=[]):
    """
    Returns an adjacency list (sequence of all [parent, child] pairs) for a root
    tree node and all its descendants in a topological ordering of the nodes.
        order == -1 : preorder traversal
        order ==  0 : inorder traversal
        order ==  1 : postorder traversal

    """
    if node is not None:
        if order == -1:
            adj_list.append([node.parent, node])
        _traversal(node.lchild, order, adj_list)

        if order == 0:
            adj_list.append([node.parent, node])
        _traversal(node.rchild, order, adj_list)

        if order == 1:
            adj_list.append([node.parent, node])
    return adj_list


class DataLogNode(object): #TODO: rename class LogNode
    """
    Keep a log of events over an agent's lifetime and logs for its progeny. Log
    nodes are linked to form a binary tree.

    """
    def __init__(self, parent=None):
        self.parent = parent
        self.lchild = None
        self.rchild = None
        self.tstamp = []
        self.estamp = []
        self.log = []

    def record(self, time_stamp, channel_id, state):
        self.tstamp.append( time_stamp )
        self.estamp.append( channel_id )
        self.log.append( state.snapshot() )

    def branch(self):
        l_node = DataLogNode(parent=self)
        self.lchild = l_node
        r_node = DataLogNode(parent=self)
        self.rchild = r_node
        return l_node, r_node

    def traverse(self, order=-1):
        # TODO: add other traversal methods/non-recursive implementations
        return _traversal(self, -1)


class Recorder(object):
    """
    Collects population snapshots in memory.

    """
    def __init__(self, agent_vars, world_vars):
        self.time = []
        self._agent_vars = agent_vars
        self._world_vars = world_vars
        for name in agent_vars:
            setattr(self, name, [])
        for name in world_vars:
            setattr(self, name, [])

    def snapshot(self, gdata, cells, time):
        self.time.append(time)
        for name in self._agent_vars:
            getattr(self, name).append( [copy(getattr(cell.state, name)) for cell in cells] )
        for name in self._world_vars:
            getattr(self, name).append( copy(getattr(gdata.state, name)))


def save_snapshot(filename, simdata):
    try:
        dfile = h5py.File(filename, 'w') #'data/stress_data.hdf5'
        dfile.create_dataset(name='time',
                             data=np.array(simdata.t))
        for dname in simdata.datasets:
            dfile.create_dataset(name=dname,
                                 data=np.array(getattr(simdata, dname)))
    finally:
        dfile.close()


def save_lineage(filename, root, var_names):
    node_list = root.traverse()
    tstamp = []
    estamp = []
    data = []
    adj_list = []
    row = 0
    for parent, child in node_list:
        pid = id(parent) if parent is not None else 0
        cid = id(child)
        tstamp.extend(child.tstamp)
        estamp.extend(child.estamp)
        data.extend(child.log)
        adj_list.append([pid, cid, row, len(child.log)])
        row += len(child.log)

    try:
        dfile = h5py.File(filename,'w')
        dfile.create_dataset(name='adj_list_info',
                             data=np.array(['parent_id', 'id', 'start_row', 'num_events'], dtype=np.bytes_))
        dfile.create_dataset(name='adj_list',
                             data=np.array(adj_list))

        dfile.create_dataset(name='timestamp',
                             data=np.array(tstamp))
        dfile.create_dataset(name='eventstamp',
                             data=np.array(estamp, dtype=np.bytes_))
        dfile.create_dataset(name='node_data_info',
                             data=np.array(var_names, dtype=np.bytes_))
        dfile.create_dataset(name='node_data',
                             data=np.array(data))
    finally:
        dfile.close()





def main():
    pass

if __name__ == '__main__':
    main()
