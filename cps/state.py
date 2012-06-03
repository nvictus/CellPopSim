"""
Name:        state

Author:      Nezar Abdennur <nabdennur@gmail.com>
Created:     23/04/2012
Copyright:   (c) Nezar Abdennur 2012

"""
#!/usr/bin/env python

from copy import copy, deepcopy
from cps.exception import LoggingError

class State(object):
    """
    Provide the state attributes of an entity according to the variable names
    specified in a model.

    """
    def __init__(self, var_names):
        self._names = []
        for name in var_names:
            setattr(self, name, None)
            self._names.append(name)

    def __copy__(self):
        other = State(self._names)
        for name in self._names:
            setattr(other, name, copy(getattr(self, name)))
        return other
# TODO: remove _names and just use __dict__, or consider using a metaclass and
# switching to __slots__ to save space?


#-------------------------------------------------------------------------------
# The following classes are for logging/recording simulation data during a
# simulation run

def default_logger(state):
    # Default function used to log snapshots of agents' states
    return [copy(getattr(state,name)) for name in state._names]

def _traversal(node, order=-1, adj_list=None):
    if adj_list is None:
        adj_list = []
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

class LoggerNode(object):
    """
    Keep a log of events over an agent's lifetime and logs for its progeny.
    Loggers are linked together as a binary tree.

    """
    def __init__(self, names, logger=default_logger, parent=None):
        self.names = names
        self.log = dict( zip(names, [ [] for name in names ]) )
        self.log['time'] = []
        self.log['channel']= []
        self._logger = logger
        self.parent = parent
        self.lchild = None
        self.rchild = None

    def record(self, time, channel_id, state):
        self.log['time'].append(time)
        self.log['channel'].append(channel_id)
        values = self._logger(state)
        if len(self.names) != len(values):
            raise LoggingError
        for name, value in zip(self.names, values):
            self.log[name].append(value)

    def branch(self):
        l_node = LoggerNode(self.names, self._logger, parent=self)
        self.lchild = l_node
        r_node = LoggerNode(self.names, self._logger, parent=self)
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
    def __init__(self, world_vars, agent_vars):
        self.world_vars = world_vars
        self.agent_vars = agent_vars
        names = ['time' , 'size'] + world_vars + agent_vars
        self.log = dict( zip(names, [[] for name in names]) )

    def record(self, time, world, agents):
        self.log['time'].append(time)
        self.log['size'].append(world.size)
        for name in self.agent_vars:
            self.log[name].append( [copy(getattr(agent.state, name)) for agent in agents] )
        for name in self.world_vars:
            self.log[name].append( copy(getattr(world.state, name)) )
