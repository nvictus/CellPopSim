"""
Name:        entity

Author:      Nezar Abdennur

Created:     23/04/2012
Copyright:   (c) Nezar Abdennur 2012
"""
#!/usr/bin/env python

from cps.channel import *
from cps.exception import SchedulingError, SimulationError
from cps.state import State, LoggerNode
from copy import copy
import heapq


#-------------------------------------------------------------------------------
# Factory functions for creating entities from model input data

def create_agent(t_init, ac_table, wc_table, var_names, logging=False, logger_args=None):
    """
    Factory for agent entities. World channels are not copied.

    """
    # make a copy of each channel instance provided
    copied = {entry.channel:copy(entry.channel) for entry in ac_table.values()}

    # build channel dependency graphs and local event schedule
    g2l_graph = {}
    for entry in wc_table.values():
        g2l_graph[entry.channel] = tuple([copied[channel] for channel in entry.wc_dependents])
    channel_dict = {}
    dep_graph = {}
    l2g_graph = {}
    sync_channels = []
    for name, entry in ac_table.items():
        channel_dict[name] = copied[entry.channel]
        dep_graph[copied[entry.channel]] = tuple([copied[channel] for channel in entry.ac_dependents])
        l2g_graph[copied[entry.channel]] = tuple(entry.wc_dependents)
        if entry.sync:
            sync_channels.append(copied[entry.channel])
    sync_channels = tuple(sync_channels)

    # create channel network/event schedule
    network = ChannelNetwork(channel_dict, dep_graph, l2g_graph, g2l_graph, sync_channels, t_init)

    # create state object
    state = State(var_names)

    # create agent
    if logging:
        node = LoggerNode(*logger_args)
        return LoggingAgent(t_init, state, network, node)
    else:
        return Agent(t_init, state, network)


def create_world(t_init, wc_table, var_names):
    """
    Factory for world entities. World channels are not copied.

    """
    # build channel dependency graph and global event schedule
    channel_dict = {}
    dep_graph = {}
    for name, entry in wc_table.items():
        channel_dict[name] = entry.channel
        dep_graph[entry.channel] = tuple([channel for channel in entry.wc_dependents])

    # create channel network/event schedule
    network = ChannelNetwork(channel_dict, dep_graph, t_init=t_init)

    # create state object
    state = State(var_names)

    # create world
    return World(t_init, state, network)



#-------------------------------------------------------------------------------
# Manage a network of simulation channels

class ChannelNetwork(object):
    """
    Holds a collection of simulation channels, their dependency structure and
    the event schedule for an entity.

    The event schedule is a simple priority queue based on a linear scan for the
    smallest element. The min element is cached until the queue is updated to
    improve lookup efficiency.

    Attributes:
        channel_dict    (dict: name -> channel)
        timetable       (dict: channel -> float)
        dep_graph       (dict: channel -> tuple of channels)
        l2g_graph       (dict: channel -> tuple of channels)
        g2l_graph       (dict: channel -> tuple of channels)
        sync_channels   (tuple of channels)

    NOTE: we could switch to an indexed heap priority queue...

    """
    def __init__(self, channel_dict, dep_graph, l2g_graph=None, g2l_graph=None, sync_channels=(), t_init=float('-inf')):
        self.channel_dict = channel_dict
        self.timetable = {channel:t_init for channel in channel_dict.values()}
        self.dep_graph = dep_graph
        self.l2g_graph = l2g_graph
        self.g2l_graph = g2l_graph
        self.sync_channels = sync_channels
        self.__next_event_time = None
        self.__next_channel = None
        self.__updated = True
        #NOTE: could use a sequence of all channels to help enforce an ordering for tie-breaking...
        #      or use 2-tuples as priority keys (event_time, index)

    def __contains__(self, channel):
        return channel in self.timetable

    def __iter__(self):
        return iter(self.timetable.keys())

    def __getitem__(self, channel):
        return self.timetable[channel]

    def __setitem__(self, channel, event_time):
        self.timetable[channel] = event_time
        self.__updated = True

    def getMin(self):
        #NOTE: min() is run on a dict_items whose order of elements is arbitrary
        #      therefore the element chosen when two channels have the same
        #      event time is arbitrary as well
        if self.__updated:
            cmin, tmin = min(self.timetable.items(), key=lambda x: x[1])
            self.__next_channel = cmin
            self.__next_event_time = tmin
            self.__updated = False
        return self.__next_channel, self.__next_event_time

    def __copy__(self):
        # make a copy of each simulation channel, mapped to the original
        orig_copied = {channel:copy(channel) for channel in self.timetable}

        # mirror the dictionary of channels
        channel_dict = {name:orig_copied[self.channel_dict[name]] for name in self.channel_dict}

        # mirror the list of gap channels
        sync_channels = tuple([orig_copied[sync] for sync in self.sync_channels])

        # mirror the dependency graphs
        dep_graph = {}
        for orig in orig_copied:
            dependencies = self.dep_graph[orig]
            dep_graph[orig_copied[orig]] = tuple([orig_copied[dependency] for dependency in dependencies])
        l2g_graph = {}
        for orig in orig_copied:
            dependencies = self.l2g_graph[orig]
            l2g_graph[orig_copied[orig]] = tuple([dependency for dependency in dependencies])
        g2l_graph= {}
        for world_channel in self.g2l_graph:
            dependencies = self.g2l_graph[world_channel]
            g2l_graph[world_channel] = tuple([orig_copied[dependency] for dependency in dependencies])

        # create a new network with cloned channels and dependency graphs
        other = ChannelNetwork(channel_dict, dep_graph, l2g_graph, g2l_graph, sync_channels)

        # copy over the event times
        for channel in self.timetable:
            other.timetable[orig_copied[channel]] = self.timetable[channel]

        # cached data (if available)
        if self.__next_event_time is not None:
            other.__next_channel = orig_copied[self.__next_channel]
            other.__next_event_time = self.__next_event_time
            other.__updated = False
        return other



#-------------------------------------------------------------------------------
# Simulation entities: agents & world

class Entity(object): #Abstract
    """
    Base class for agent/world simulation entities.
    Implements most of the internal application-side interface.

    The External API provided:
        stop() - disable further execution on the entity
        fireChannel() - fire a channel "manually" from within another channel

    """
    def __init__(self, time, state, network):
        if any([network[channel] < time for channel in network]):
            raise SimulationError("Cannot create entity: some channel's event time precedes the entity's clock.")
        self.clock = time
        self.state = state
        self.network = network
        self.is_enabled = True
        self.is_modified = False
        self._prev_channel = None

    def start(self):
        self.is_enabled = True

    def stop(self):
        self.is_enabled = False

    def fireChannel(self, name, cargo, t_fire, queue, source=None):
        """
        Fire a channel "manually". Rescheduling dependencies will be invoked if
        the channel modifies the entity. However, cross-dependencies (i.e., l2g
        or g2l) will not be invoked.
        NOTE: need to supply the firing time.

        """
        channel = self.network.channel_dict[name]
        if t_fire < self.clock:
            raise FiringError(channel, self.clock, t_fire)
        is_mod = channel.fireEvent(self, cargo, self.clock, t_fire, queue)
        self.clock = t_fire

        # reschedule channel that just fired
        event_time = channel.scheduleEvent(self, cargo, self.clock, source)
        if event_time < self.clock:
            raise SchedulingError(channel, self.clock, event_time)
        self.network[channel] = event_time

        # reschedule dependent channels
        if is_mod:
            for dependent in self.network.dep_graph[channel]:
                event_time = dependent.scheduleEvent(self, cargo, self.clock, source)
                if event_time < self.clock:
                    raise SchedulingError(dependent, self.clock, event_time)
                self.network[dependent] = event_time

    def scheduleAllChannels(self, cargo, source=None):
        tmin = float('inf')
        cmin = None
        for channel in self.network:
            event_time = channel.scheduleEvent(self, cargo, self.clock, source)
            if event_time < self.clock:
                raise SchedulingError(channel, self.clock, event_time)
            elif event_time < tmin:
                tmin = event_time
                cmin = channel
            self.network[channel] = event_time
        return tmin

    def fireNextChannel(self, cargo, queue):
        cmin, tmin = self.network.getMin()
        # fire channel
        self.is_modified = cmin.fireEvent(self, cargo, self.clock, tmin, queue)
        self.clock = tmin

        # reschedule channel that just fired
        event_time = cmin.scheduleEvent(self, cargo, self.clock, None)
        if event_time < self.clock:
            raise SchedulingError(cmin, self.clock, event_time)
        self.network[cmin] = event_time

        # remember channel that just fired
        self._prev_channel = cmin

    def rescheduleDependentChannels(self, cargo, source=None):
        if self.is_modified:
            for dependent in self.network.dep_graph[self._prev_channel]:
                # reschedule dependent channel
                event_time = dependent.scheduleEvent(self, cargo, self.clock, source)
                if event_time < self.clock:
                    raise SchedulingError(dependent, self.clock, event_time)
                self.network[dependent] = event_time

    def _get_next_event_time(self):
        cmin, tmin = self.network.getMin()
        return tmin
    next_event_time = property(fget=_get_next_event_time)


class World(Entity):
    """
    World entity.

    Attributes:
        clock       (float)
        state       (cps.state.State)
        network     (cps.entity.ChannelNetwork)
        is_enabled  (bool)
        is_modified (bool)

    """
    def crossScheduleL2G(self, cargo, source_agent):
        """
        Takes as input the agent who fired the offending event.
        Reschedules affected world channels.

        """
        if source_agent.is_modified:
            prev_channel = source_agent._prev_channel
            for world_channel in source_agent.network.l2g_graph[prev_channel]:
                # reschedule world channel that depends on source agent
                event_time = world_channel.scheduleEvent(self, cargo, self.clock, source_agent)
                if event_time < self.clock:
                    raise SchedulingError(world_channel, self.clock, event_time)
                self.network[world_channel] = event_time

    def crossScheduleL2GAsync(self, cargo, world_channels):
        """
        Different version for the Asynchronous Method algorithm.
        This takes the collection of world channels to reschedule as input
        rather than the agents who fired the offending events.

         """
        for world_channel in world_channels:
            event_time = world_channel.scheduleEvent(self, cargo, self.clock, source_agent)
            if event_time < self.clock:
                raise SchedulingError(world_channel, self.clock, event_time)
            self.network[world_channel] = event_time


class Agent(Entity):
    """
    Agent entity. Agents can be cloned so as to introduce new offspring into
    the population. They also need to be synchronized before a world event.

    Attributes:
        clock       (float)
        state       (cps.state.State)
        network     (cps.entity.ChannelNetwork)
        is_enabled  (bool)
        is_modified (bool)

    External API:
        stop()
        fireChannel()
        clone()

    """
    def __init__(self, time, state, network):
        super(Agent, self).__init__(time, state, network)
        self._parent = None

    def __copy__(self):
        time = self.clock
        state = copy(self.state)
        network = copy(self.network) #copies event schedule + cached min element
        other = Agent(time, state, network)
        return other

    def clone(self):
        # Cloned agents are bound to their parent before they are added to the
        # population. This marker should be removed when the new agent is added.
        if self._parent is not None:
            raise SimulationError("Cannot clone an agent that is not in the population.")
        other = self.__copy__()
        other._parent = self
        return other

    def finalizePrevEvent(self):
        """ Called by simulator after a cloned agent is popped from queue """
        # Get the channel that cloned the agent (i.e. is still firing right now)
        channel, event_time = self.network.getMin()
        # NOTE: In principle, doing this could yield the wrong channel when
        #       there is a tie for the min event. But we are OK because we mirrored
        #       the cached min channel when the agent was cloned (see ChannelNetwork.__copy__).
        #       If this behavior changes, it could cause a subtle bug.

        self._prev_channel = channel
        self.clock = event_time

        # Assume we always want to invoke dependencies on the new agent. It doesn't hurt anyway.
        self.is_modified = True

        # Remove marker (unbind the parent)
        self._parent = None

    def reschedulePrevChannel(self, cargo, source=None):
        """ Called by simulator after a cloned agent is popped from queue """
        prev = self._prev_channel
        event_time = prev.scheduleEvent(self, cargo, self.clock, source)
        if event_time < self.clock:
            raise SchedulingError(prev_channel, self.clock, event_time)
        self.network[prev] = event_time

    def synchronize(self, tbarrier, world, queue, source=None):
        """
        Synchronize time-driven channels by firing them at a specified time
        barrier.

        """
        for channel in self.network.sync_channels:
            is_mod = channel.fireEvent(self, world, self.clock, tbarrier, queue)
            if is_mod:
                for dependent in self.network.dep_graph[channel]:
                    # NOTE:some of these rescheds may be redundant if any of the dependents
                    # are sync channels that are still waiting to fire in the outer loop...
                    event_time = dependent.scheduleEvent(self, world, tbarrier, source)
                    if event_time < self.clock:
                        raise SchedulingError(dependent, tbarrier, event_time)
                    self.network[dependent] = event_time
        self.clock = tbarrier

    def crossScheduleG2L(self, cargo, world):
        """
        Takes as input the world entity which fired an offending event.
        Reschedules affected agent channels.

        """
        if world.is_modified:
            prev_channel = world._prev_channel
            for agent_channel in self.network.g2l_graph[prev_channel]:
                # reschedule world-dependent local channels
                event_time = agent_channel.scheduleEvent(self, cargo, self.clock, world)
                if event_time < self.clock:
                    raise SchedulingError(agent_channel, self.clock, event_time)
                self.network[agent_channel] = event_time

    def getDependentChannels(self):
        return self.network.dep_graph[self._prev_channel]

    def getDependentWorldChannels(self):
        return self.network.l2g_graph[self._prev_channel]


class LoggingAgent(Agent):
    """
    Agent entity subclass that logs every event to create a lineage tree of
    state and event histories.

    Additional attributes:
        node    (cps.state.LoggerNode)

    """
    def __init__(self, time, state, network, logger=None):
        super(LoggingAgent, self).__init__(time, state, network)
        self.node = logger

    def __copy__(self):
        time = self.clock
        state = copy(self.state)
        network = copy(self.network)
        other = LoggingAgent(time, state, network)

        # Branch datalog into two new nodes
        l_node, r_node = self.node.branch()
        self.node = l_node
        other.node = r_node
        return other

    def fireChannel(self, name, cargo, t_fire, queue, source=None):
        super(LoggingAgent, self).fireChannel(name, cargo, t_fire, queue, source)
        self.node.record(self.clock, self.network.channel_dict[name].id, self.state) #SHOULD THESE BE RECORDED?

    def fireNextChannel(self, cargo, queue):
        super(LoggingAgent, self).fireNextChannel(cargo, queue)
        self.node.record(self.clock, self._prev_channel.id, self.state)

        # NOTE FOR CLONING EVENTS: the final state of the first new agent (self)
        #   at the completion of the division event gets logged as the first
        #   event on its new datalog.
        #
        # We don't have access to the cloned agent in the fireNextChannel()
        # method. It should be lying in the agent queue. Its first event is
        # "incomplete" because it doesn't get finalized when fireNextChannel()
        # returns. Instead, the event is finalized when the agent is retrieved
        # from the queue using finalizePrevEvent(): we record its state to its
        # datalog.

    def finalizePrevEvent(self):
        super(LoggingAgent, self).finalizePrevEvent()
        # Log the event that caused division, recording final state of the newborn
        self.node.record(self.clock, self._prev_channel.id, self.state)



#-------------------------------------------------------------------------------
# Priority queue for adding/removing agents from the population

class AgentQueue(object):
    """
    A queue of agents to be introduced or removed from the population at
    specified times according to the specified action. Agents are retrieved in
    time-stamp order.

    Constants:
        ADD_AGENT
        DELETE_AGENT

    Attributes:
        heap (list): binary heap holding agents

    """
    ADD_AGENT = 1
    DELETE_AGENT = -1

    class Entry(object):
        def __init__(self, priority_key, item, action=None):
            self.priority_key = priority_key
            self.item = item
            self.action = action

        def __lt__(self, other):
            return self.priority_key < other.priority_key

    def __init__(self):
        self.heap = []

    def __len__(self):
        return len(self.heap)

    def enqueue(self, action, agent, priority_key):
        if action == AgentQueue.ADD_AGENT:
            if agent._parent:
                heapq.heappush( self.heap, AgentQueue.Entry(priority_key, agent, action) )
            else:
                raise SimulationError("The agent queued for insertion is already in the population.")
        elif action == AgentQueue.DELETE_AGENT:
            if agent._parent:
                raise SimulationError("The agent queued for deletion is not in the population.")
            else:
                agent.stop()
                heapq.heappush( self.heap, AgentQueue.Entry(priority_key, agent, action) )
        else:
            raise SimulationError("Invalid action.")

    def dequeue(self):
        try:
            entry = heapq.heappop( self.heap )
        except IndexError:
            raise KeyError
        return entry.action, entry.item
