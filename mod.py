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

# Simulation channels
class AgentChannel(Channel):
    """
    Base class for an agent simulation channel.

    """
    def scheduleEvent(self, agent, world, time, source=None):
        # return putative time of next event
        return float('inf')

    def fireEvent(self, agent, world, time, event_time, add_queue, rem_queue):
        # return boolean specifying if entity was modified
        return False

class WorldChannel(Channel):
    """
    Base class for global simulation channel.

    """
    def scheduleEvent(self, world, agents, time, source=None):
        # return event time
        return float('inf')

    def fireEvent(self, world, agents, time, event_time, add_queue, rem_queue):
        # return boolean
        return False


#Simulation engines
class WCEngine(Engine):
    """
    Engine for world simulation channels.

    """
    def __init__(self, time, channels, dep_graph):
        self.clock = time
        self.dep_graph = dep_graph
        self.timetable = {channel:time for channel in channels}
        self._next_channel = None
        self._next_event_time = None
        self._is_modified = False

    def rescheduleAgentDependentChannels(self, agents, source):
        for channel in source._engine.l_to_g[source._engine._next_channel]:
            event_time = channel.scheduleEvent(entity, agents, self.clock, source)
            if event_time < self.clock:
                raise SchedulingError(source, chnnel, self.clock, event_time)
            self._engine.timetable[channel] = event_time
        cmin, tmin = min(self._engine.timetable.items(), key=lambda x: x[1])
        self._engine._next_channel = cmin
        self._engine._next_event_time = tmin
        return tmin

class ACEngine(Engine):
    """
    Engine for agent simulation channels.

    """
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
        #TODO: log the triggering event in the parent node and spawn two new history log nodes
        # child engine needs to know what channel triggered its creation...for rescheduling later
        new_engine._next_channel = self._next_channel
        return new_engine

    def rescheduleWorldDependentChannels(self, world):
        for channel in self._engine.g_to_l[world._engine._next_channel]:
            event_time = channel.scheduleEvent(entity, world, world._engine.clock, None)
            if event_time < world._engine.clock:
                raise SchedulingError(world, channel, world_engine.clock, event_time)
            self._engine.timetable[channel] = event_time
        cmin, tmin = min(self._engine.timetable.items(), key=lambda x: x[1])
        self._engine._next_channel = cmin
        self._engine._next_event_time = tmin
        return tmin


class Entity(object):
    """
    Generic class. Encapsulate state and engine.
    Engine queries and modifies state.
    Should fulfill two interfaces:
        one for client (IEntity)
        one for manager (IEngine)

    """
    # Interface exposed to client
    def start(self):
        self._enabled = True

    def stop(self):
        self._enabled = False

    def fireChannel(self, name, cargo, aq, rq):
        self.is_mod = self._engine.fireChannel(name, self, cargo, aq, rq)
        self._engine.rescheduleChannels(self, cargo, None, self.is_mod)

    # Interface exposed to manager
    def scheduleAllChannels(self, cargo, source=None):
        return self._engine.scheduleAllChannels(self, cargo, source)

    def rescheduleChannels(self, cargo, source=None):
        return self._engine.rescheduleChannels(self, cargo, source, self.is_mod)

    def closeGaps(self, cargo, aq, rq, source=None):
        return self._engine.closeGaps(self, cargo, source, self.is_mod)

    def fireNextChannel(self, cargo, aq, rq):
        self.is_mod = self._engine.fireNextChannel(self, cargo, aq, rq)


# Simulation entities
class World(Entity):
    """
    State consists of data common to all agents.
    Engine manipulats the state using world channels.

    """
    def __init__(self, state, world_engine):
        self._enabled = True
        self.state = state
        self._engine = world_engine

class Agent(Entity):
    """
    State consists of agent-specific information.
    Engine manipulates the state using agent channels.

    """
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





#-------------------------------------------------------------------------------
def main():
    pass

if __name__ == '__main__':
    main()