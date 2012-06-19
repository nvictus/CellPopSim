"""
Name:        logging

Author:      Nezar Abdennur <nabdennur@gmail.com>
Created:     23/04/2012
Copyright:   (c) Nezar Abdennur 2012

"""
#!/usr/bin/env python

from copy import copy, deepcopy
from cps.exception import LoggingError

#-------------------------------------------------------------------------------
# The following classes are for logging/recording simulation data during a
# simulation run

class Logger(object):
    def __init__(self, names, logging_fcn):
        raise NotImplementedError

    def record(self, time, *args):
        raise NotImplementedError

def default_loggingfcn(log, time, entity):
    """
    Default function used to log snapshots of agents' states.

    """
    for name in entity._names:
        log[name].append( copy(getattr(entity, name)) ) 

def _bfs_traversal(node):
    """
    Iterative breadth-first-search traversal of a binary tree.
    Visits nodes in level-order.

    """
    queue = []
    observed = set([None])

    if node not in observed:
        observed.add(node)
        queue.append(node)

    while queue:
        node = queue.pop(0)
        yield node

        for child in node.children:
            if child not in observed:
                observed.add(child)
                queue.append(child)
    return

def _dfs_traversal(node, order=-1):
    """
    Iterative depth-first-search traversal of a binary tree.
        order == -1 : preorder visitation
        order ==  0 : inorder visitation
        order ==  1 : postorder visitation

    """
    stack = []
    observed = set([None])

    if node not in observed:
        if order == -1:
            yield node
        observed.add(node)
        stack.append([node, node.children])
    
    while stack:
        node, children = stack.pop()
        while children:
            if order == 0 and len(children)==1:
                yield node
            child = children.pop(0)
            if child not in observed:
                observed.add(child) 
                stack.append([node, children])
                node, children = child, child.children
                if order == -1:
                    yield node
        if order == 1:
            yield node
    return
            
def _dfs_recursive(node, order=-1):
    """
    Does recursive depth-first-search traversal of a binary tree.
        order == -1 : preorder visitation
        order ==  0 : inorder visitation
        order ==  1 : postorder visitation

    """
    if node is not None:
        if order == -1:
            yield node
        _dfs_traversal_recursive(node.lchild, order)

        if order == 0:
            yield node
        _dfs_traversal_recursive(node.rchild, order)

        if order == 1:
            yield node
    return


class LoggerNode(object):
    """
    Logger keeps a log of events and recorded state over an agent's lifetime
    while linking to the logs of the agent's progeny. Logger nodes are linked
    together forming a binary tree.

    """
    def __init__(self, names, logging_fcn=None, parent=None):
        self.parent = parent
        self.lchild = None
        self.rchild = None
        self._names = names
        if logging_fcn is not None:
            self._logging_fcn = logging_fcn
        else:
            self._logging_fcn = default_loggingfcn
        self.log = dict( zip(names, [ [] for name in names ]) )
        self.log['time'] = []
        self.log['channel']= []

    def __iter__(self):
        for child in [self.lchild, self.rchild]:
            yield child

    @property
    def children(self):
        return [self.lchild, self.rchild]

    def record(self, time, channel_id, entity):
        self.log['time'].append(time)
        self.log['channel'].append(channel_id)
        self._logging_fcn(self.log, time, entity)

    def branch(self):
        l_node = LoggerNode(self._names, self._logging_fcn, parent=self)
        self.lchild = l_node
        r_node = LoggerNode(self._names, self._logging_fcn, parent=self)
        self.rchild = r_node
        return l_node, r_node

    def traverseBFS(self):
        """
        Returns a generator that performs a breadth-first traversal over the tree
        of logger nodes.

        """
        return _bfs_traversal(self)

    def traverseDFS(self, order=-1):
        """
        Returns a generator that performs a depth-first traversal over the tree
        of logger nodes.

        """
        return _dfs_traversal(self, order)

    def adjacencyList(self):
        """ 
        Returns an adjacency list (sequence of all [parent, child] pairs) for a root
        tree node and all its descendants in a topological ordering of the nodes.

        """
        nodes = _dfs_traversal(node)
        return [ (node.parent, node) for node in nodes]


class Recorder(object):
    """
    Records and collects a sequence of population snapshots.

    """
    def __init__(self, world_names, agent_names, recording_fcn=None):
        self.world_names = world_names
        self.agent_names = agent_names
        names = ['time' , 'size'] + world_names + agent_names
        self.log = dict([(name, []) for name in names])
        if recording_fcn is not None:
            self._recording_fcn = recording_fcn
        else:
            self._recording_fcn = self._record

    def record(self, time, world, agents):
        self.log['time'].append(time)
        self.log['size'].append(world.size)
        self._recording_fcn(self.log, time, world, agents)

    def _record(self, time, world, agents):
        for name in self.agent_vars:
            self.log[name].append( [copy(getattr(agent, name)) for agent in agents] )
        for name in self.world_vars:
            self.log[name].append( copy(getattr(world, name)) )        


def make_logger(names, logging_fcn=default_loggingfcn):
    pass

def make_recorder(world_names, agent_names, recording_fcn=None):
    pass

# class State(object):
#     """
#     Provide the state attributes of an entity according to the variable names
#     specified in a model.

#     """
#     def __init__(self, var_names):
#         for name in var_names:
#             setattr(self, name, None)

#     def __copy__(self):
#         other = State(self.__dict__)
#         for name in self.__dict__:
#             setattr(other, name, copy(getattr(self, name)))
#         return other
# # TODO: consider using a metaclass and switching to __slots__ to save space?