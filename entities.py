#-------------------------------------------------------------------------------
# Name:        entities
# Purpose:
#
# Author:      Nezar
#
# Created:     11/01/2012
# Copyright:   (c) Nezar 2012
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python

from base import *
from copy import copy
import heapq


class WCEngine(Engine):
    def __init__(self, time, channels, dep_graph):
        self.clock = time
        self.dep_graph = dep_graph
        self.timetable = {channel:time for channel in channels}
        self._next_channel = None
        self._next_event_time = None
        self._is_modified = False

class ACEngine(Engine):
    def __init__(self, time, channels, dep_graph):
        self.clock = time
        self.dep_graph = dep_graph
        self.timetable = {channel:time for channel in channels}
        self._next_channel = None
        self._next_event_time = None
        self._is_modified = False

    def __copy__(self):
        copied = {channel:copy(channel) for channel in self.timetable}
        dep_graph = {}
        for channel in self.timetable:
            dependencies = self.dep_graph[channel]
            dep_graph[copied[channel]] = (copied[dependency] for dependency in dependencies)
        new_engine = AgentEngine(self.time, copied.values(), dep_graph)
        for channel in self.timetable:
            new_engine.timetable[copied[channel]] = self.timetable[channel]
        return new_engine

class World(Entity):
    def __init__(self, state, world_engine):
        self._enabled = True
        self.state = state
        self._engine = world_engine

class Agent(Entity):
    def __init__(self, state, agent_engine):
        self._enabled = True
        self.state = state
        self._engine = agent_engine

    def clone(self):
        new_state = copy(self.state)
        new_engine = copy(self._engine)
        return Agent(new_state, new_engine)

class LineageAgent(Agent):
    pass

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








def main():
    pass

if __name__ == '__main__':
    main()