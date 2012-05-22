"""
Name:        state

Author:      Nezar Abdennur <nabdennur@gmail.com>
Created:     23/04/2012
Copyright:   (c) Nezar Abdennur 2012

"""
#!/usr/bin/env python

from copy import copy, deepcopy

def default_logger(state):
    # Default function used to log snapshots of agents' states
    return [copy(getattr(state,name)) for name in state._names]

class State(object):
    """
    Provide the state attributes of an entity according to the variable names
    specified in a model.

    """
    def __init__(self, var_names, logger=default_logger):
        self._do_log = logger
        self._names = []
        for name in var_names:
            setattr(self, name, None)
            self._names.append(name)

    def __copy__(self):
        other = State(self._names, self._do_log)
        for name in self._names:
            setattr(other, name, copy(getattr(self, name)))
        return other

    def snapshot(self):
        return self._do_log(self)


#-------------------------------------------------------------------------------
# The following classes are for logging/recording simulation data during a
# simulation run

def _traversal(node, order=-1, adj_list=[]):
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

class DataLogNode(object):
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
        """
        Returns an adjacency list (sequence of all [parent, child] pairs) for a root
        tree node and all its descendants in a topological ordering of the nodes.
            order == -1 : preorder traversal
            order ==  0 : inorder traversal
            order ==  1 : postorder traversal

        """
        # TODO: add other traversal methods/non-recursive implementations
        return _traversal(self, order, [])


class Recorder(object):
    """
    Collects population snapshots in memory.

    """
    def __init__(self, agent_vars, world_vars):
        self.time = []
        self.size = []
        self._agent_vars = agent_vars
        self._world_vars = world_vars
        for name in agent_vars:
            setattr(self, name, [])
        for name in world_vars:
            setattr(self, name, [])

    def record(self, time, world, agents):
        self.time.append(time)
        self.size.append(world.size)
        for name in self._agent_vars:
            getattr(self, name).append( [copy(getattr(agent.state, name)) for agent in agents] )
        for name in self._world_vars:
            getattr(self, name).append( copy(getattr(world.state, name)) )

    def getFields(self):
        return self._world_vars + self._agent_vars




