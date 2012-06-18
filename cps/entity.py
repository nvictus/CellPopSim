"""
Name:        entity

Author:      Nezar Abdennur

Created:     23/04/2012
Copyright:   (c) Nezar Abdennur 2012
"""
#!/usr/bin/env python

from cps.channel import *
from cps.logging import LoggerNode
from cps.exception import SchedulingError, FiringError, SimulationError
from cps.simulator import FMSimulator, AMSimulator


from copy import copy
import collections
import heapq
import math


#-------------------------------------------------------------------------------
# Manage a network of simulation channels

class ChannelSchedule(dict):
    """
    A simple prioritized collection that uses linear scan to find the smallest
    item (channel with earliest event time). The min item is cached until the 
    queue is updated to improve lookup efficiency.

    """
    #NOTE: we can make a subclass where __setitem__ stores the timetable values
    #as pairs [time, rank] to implement a ranked priority queue for tie-breaking
    #between channels with the same event time...
    #
    #NOTE: we could also switch to an indexed heap-based priority queue...

    def __init__(self, *args):
        self.update(dict(*args))
        if not self:
            raise ValueError('Schedule requires at least one channel')
        self.__earliest_channel = None
        self.__earliest_time = None
        self.__updated = True

    def __setitem__(self, channel, event_time):
        super(ChannelSchedule, self).__setitem__(channel, event_time)
        channel._event_time = event_time
        self.__updated = True

    def earliestItem(self):
        #NOTE: min() is run on a dict_items whose order of elements is arbitrary
        #      therefore the element chosen when two channels have the same
        #      event time is arbitrary as well
        if self.__updated:
            cmin, tmin = min(self.items(), key=lambda x: x[1])
            self.__earliest_channel = cmin
            self.__earliest_time = tmin
            self.__updated = False
        return self.__earliest_channel, self.__earliest_time


class Scheduler(object):
    """
    Manages the simulation channels assigned to an entity. Provides an updatable event 
    schedule mapping channels to their event times, and exposes the channels, their 
    dependency structure and the entity's clock.

    Attributes:
        clock           float
        enabled         bool  #TODO: drop this?
        channel_dict    (dict: name -> channel)
        dep_graph       (dict: channel -> tuple of channels)
        *l2g_graph      (dict: channel -> tuple of channels)
        *g2l_graph      (dict: channel -> tuple of channels)
        *sync_channels  (tuple of channels)

    *applies only to agent schedulers

    """
    def __init__(self, time, timetable, dep_graph, l2g_graph=None, g2l_graph=None, sync_channels=()):
        if any([t < time for t in timetable.values()]):
           raise SchedulingError("Cannot create scheduler: some channel's event time precedes the current clock time.")
        elif math.isnan(time):
            raise ValueError("Clock time cannot be NaN")
        self._timetable = ChannelSchedule(timetable)
        self.clock = time
        self.enabled = True
        self.channel_dict = {channel._id:channel for channel in timetable}
        self.dep_graph = dep_graph
        if l2g_graph is not None:
            self.l2g_graph = l2g_graph
            self.g2l_graph = g2l_graph
            self.sync_channels = sync_channels
            # check that no sync channel has sync channel dependents
            for c in sync_channels:
                if any([dependent in sync_channels for dependent in dep_graph[c]]):
                    raise ValueError("Sync channels should not sync channel dependents.")

    @staticmethod
    def agentSchedulerFromModel(t_init, ac_table, wc_table):
        """
        World channels are not copied.

        """
        # make a copy of each channel instance provided
        copied = {entry.channel:copy(entry.channel) for entry in ac_table.values()}
        timetable = dict( zip(copied.values(), [t_init]*len(copied)) )

        # build channel dependency graphs and local event schedule
        g2l_graph = {}
        for entry in wc_table.values():
            g2l_graph[entry.channel] = tuple([copied[channel] for channel in entry.wc_dependents])
        dep_graph = {}
        l2g_graph = {}
        sync_channels = []
        for entry in ac_table.values():
            dep_graph[copied[entry.channel]] = tuple([copied[channel] for channel in entry.ac_dependents])
            l2g_graph[copied[entry.channel]] = tuple(entry.wc_dependents)
            if entry.sync:
                sync_channels.append(copied[entry.channel])
        sync_channels = tuple(sync_channels)
        return Scheduler(t_init, timetable, dep_graph, l2g_graph, g2l_graph, sync_channels)

    @staticmethod
    def worldSchedulerFromModel(t_init, wc_table):
        """
        World channels are not copied.

        """
        # build channel dependency graph and global event schedule
        timetable = {entry.channel:t_init for entry in wc_table.values()}
        dep_graph = {}
        for entry in wc_table.values():
            dep_graph[entry.channel] = tuple([channel for channel in entry.wc_dependents])
        return Scheduler(t_init, timetable, dep_graph)

    @property
    def next_event_time(self):
        return self._timetable.earliestItem()[1]

    def __contains__(self, channel):
        return channel in self._timetable

    def __iter__(self):
        return iter(self._timetable.keys())

    def __getitem__(self, channel):
        return self._timetable[channel]

    def __setitem__(self, channel, event_time):
        if event_time < self.clock: #catch NaNs here too?
            raise SchedulingError
        else:
            self._timetable[channel] = event_time

    def __copy__(self):
        # make a copy of each simulation channel, mapped to the original
        orig_copied = {channel:copy(channel) for channel in self}
        # mirror the timetable
        timetable = ChannelSchedule({orig_copied[channel]:time for channel, time in self._timetable.items()})
        # mirror the dictionary of channels
        channel_dict = {name:orig_copied[self.channel_dict[name]] for name in self.channel_dict}
        # mirror the dependency graph
        dep_graph = {}
        for orig in orig_copied:
            dependencies = self.dep_graph[orig]
            dep_graph[orig_copied[orig]] = tuple([orig_copied[dependency] for dependency in dependencies])
        # create a new network with cloned channels and dependency graphs
        other = self.__class__.__new__(self.__class__)
        other.clock = self.clock
        other.enabled = self.enabled
        other.channel_dict = channel_dict
        other.dep_graph = dep_graph
        other._timetable = timetable
        if hasattr(self, 'l2g_graph'):
            # mirror the cross-dependency graphs
            l2g_graph = {}
            for orig in orig_copied:
                dependencies = self.l2g_graph[orig]
                l2g_graph[orig_copied[orig]] = tuple([dependency for dependency in dependencies])
            g2l_graph= {}
            for world_channel in self.g2l_graph:
                dependencies = self.g2l_graph[world_channel]
                g2l_graph[world_channel] = tuple([orig_copied[dependency] for dependency in dependencies])
            # mirror the list of sync channels
            sync_channels = tuple([orig_copied[sync] for sync in self.sync_channels])
            # add extra attributes
            other.l2g_graph = l2g_graph
            other.g2l_graph = g2l_graph
            other.sync_channels = sync_channels
        #if self._curr_channel is not None:
        #    other._curr_channel = orig_copied[self._curr_channel]
        return other

    def next(self):
        cmin, tmin = self._timetable.earliestItem()
        return cmin, tmin



#-------------------------------------------------------------------------------
# Simulation entities: agents & world

class BaseEntity(object):
    """
    Base class for agent/world simulation entities.
    When passed to simulation channel methods, entities provide a set of 
    user-defined state variables. Attributes and methods with leading 
    underscores make up the internal API for the simulator.

    Attributes:
        _names
        _enabled
        _is_modified
        _scheduler
        _simulator
        _curr_channel

    """
    def __init__(self, state_names, scheduler, simulator):
        self._names = state_names
        self._scheduler = scheduler
        self._simulator = simulator
        self._enabled = True
        self._is_modified = False
        self._curr_channel = None
        for name in state_names:
            setattr(self, name, None)

    @property
    def _time(self):
        return self._scheduler.clock

    @property
    def _next_event_time(self):
        return self._scheduler.next()[1]

    def _scheduleAllChannels(self):
        """
        Schedule all channels belonging to the entity.
        Return the earliest event time.

        """
        scheduler = self._scheduler
        simulator = self._simulator
        cargo = simulator.agents if isinstance(self, World) else simulator.world
        tmin = float('inf')
        cmin = None
        for channel in scheduler:
            scheduler[channel] = tsched = channel.scheduleEvent(self, cargo, scheduler.clock, None)
            if tsched < tmin:
                tmin = tsched
                cmin = channel
        return tmin

    def _processNextChannel(self):
        """
        Fire the earliest channel.
        Advance the clock to the event time.
        Enqueue any cloned agents and process immediately if possible.
        Reschedule the channel.
        Reschedule internal dependent channels if entity was changed.

        """
        scheduler = self._scheduler
        simulator = self._simulator
        cargo = simulator.agents if isinstance(self, World) else simulator.world
        # get next channel
        cnext, event_time = scheduler.next()
        self._curr_channel = cnext
        self._curr_event_time = event_time
        # fire channel
        self._is_modified = cnext.fireEvent(self, cargo, scheduler.clock, event_time)
        scheduler.clock = event_time
        if cnext._new_agents:
            # enqueue offspring
            self._enqueue_new_agents(cnext)
        if isinstance(simulator, FMSimulator) or isinstance(self, World):
            # process new agents
            simulator._processAgentQueue()
        # reschedule
        scheduler[cnext] = cnext.scheduleEvent(self, cargo, scheduler.clock, None)
        if self._is_modified:
            for dependent in scheduler.dep_graph[cnext]:
                scheduler[dependent] = dependent.scheduleEvent(self, cargo, scheduler.clock, None)

    def _fire_nested(self, channel, event_time, reschedule=False, source=None, **kwargs):
        """
        Fire the nested channel provided.
        Enqueue any cloned agents and process immediately if possible.
        If specified, reschedule the channel and internal dependent channels.
        ***Only advance the clock if rescheduling takes place!
        """
        scheduler = self._scheduler
        if channel not in scheduler:
            raise SimulationError
        simulator = self._simulator
        cargo = simulator.agents if isinstance(self, World) else simulator.world
        # fire channel
        is_modified = channel.fireEvent(self, cargo, scheduler.clock, event_time, **kwargs)
        if channel._new_agents:
            # enqueue offspring
            self._enqueue_new_agents(channel)
        if isinstance(simulator, FMSimulator) or isinstance(self, World):
            # process new agents
            simulator._processAgentQueue()
        if reschedule:
            scheduler.clock = event_time #Advance clock ONLY if we are rescheduling!!!
            scheduler[channel] = channel.scheduleEvent(self, cargo, scheduler.clock, source)
            if is_modified:
                for dependent in scheduler.dep_graph[channel]:
                    scheduler[dependent] = dependent.scheduleEvent(self, cargo, scheduler.clock, source)
        return is_modified

    def _reschedule(self, channel, dependents=False, source=None):
        """
        Reschedule the channel provided.
        Reschedule internal dependent channels if specified.
        """
        scheduler = self._scheduler
        if channel not in scheduler:
            raise SimulationError
        simulator = self._simulator
        cargo = simulator.agents if isinstance(self, World) else simulator.world
        # reschedule specified channel
        scheduler[channel] = channel.scheduleEvent(self, cargo, scheduler.clock, source)
        # reschedule its internal dependent channels
        if dependents:
            for dependent in scheduler.dep_graph[channel]:
                scheduler[dependent] = dependent.scheduleEvent(self, cargo, scheduler.clock, source)

    def _enqueue_new_agents(self, channel):
        scheduler = self._scheduler
        while channel._new_agents:
            d = channel._new_agents.pop(0)
            self._prepare_new_agent(d)
            q = self._simulator.agent_queue
            q.enqueue(q.ADD_AGENT, d, channel._event_time) # parent=self

    def _prepare_new_agent(self, new_agent):
        scheduler = new_agent._scheduler
        if isinstance(self, Agent):
            channel = new_agent._curr_channel
            world = new_agent._simulator.world
            scheduler[channel] = channel.scheduleEvent(new_agent, world, scheduler.clock, None)
            if self._is_modified:
                for dependent in scheduler.dep_graph[channel]:
                    scheduler[dependent] = dependent.scheduleEvent(new_agent, world, scheduler.clock, None)
        if isinstance(self, LoggedAgent):
            new_agent._logger.record(scheduler.clock, new_agent._curr_channel._id, new_agent)

    # def _rescheduleFired(self, dependents=True, source=None):
    #     # reschedule channel that just fired and dependent channels
    #     scheduler = self._scheduler
    #     simulator = self._simulator
    #     cargo = simulator.agents if isinstance(self, World) else simulator.world
    #     channel = self._curr_channel
    #     scheduler[channel] = channel.scheduleEvent(self, cargo, firing_time, source)
    #     if dependents:
    #         for dependent in scheduler.dep_graph[channel]:
    #             scheduler[dependent] = dependent.scheduleEvent(self, cargo, scheduler.clock, source)

    # def _fire(self, channel_name, **kwargs):
    #   """ NOTE: cross-dependencies (i.e., l2g or g2l) will not be invoked. """
    #   scheduler = self._scheduler
    #   firing_time = scheduler.clock # need to supply
    #   cargo = self._simulator.agents
    #   # fire specified channel
    #   channel = scheduler.channel_dict[channel_name]
    #   self._curr_channel = channel
    #   time = scheduler.clock
    #   scheduler.clock = firing_time
    #   self._is_modified = channel.fireEvent(self, cargo, time, firing_time, **kwargs)

    # def _resched(self, channel_name, source=None, dependents=False):
    #   """ NOTE: cross-dependencies (i.e., l2g or g2l) will not be invoked. """
    #   scheduler = self._scheduler
    #   cargo = self._simulator.agents
    #   # find specified channel
    #   channel = scheduler.channel_dict[channel_name]
    #   # reschedule channel and dependent channels
    #   scheduler[channel] = channel.scheduleEvent(self, cargo, scheduler.clock, source)
    #   if dependents:
    #   for dependent in scheduler.dep_graph[channel]:
    #       scheduler[dependent] = dependent.scheduleEvent(self, cargo, scheduler.clock, source)

class World(BaseEntity):
    """
    World entity.

    """
    def _rescheduleFromAgent(self, source_agent=None):
        # reschedule agent-dependent world channels
        scheduler = self._scheduler
        agents = self._simulator.agents
        for wchannel in source_agent._getDependentWCs():
            scheduler[wchannel] = wchannel.scheduleEvent(self, agents, scheduler.clock, source_agent)

class Agent(BaseEntity):
    """
    Agent entity. Agents can be copied so as to introduce new offspring into
    the population or queued up for removal from the population. They can also 
    synchronize their schedulers to the world clock before a world event.

    Additional attributes:
        _parent (temporary marker on a cloned agent)

    """
    def __init__(self, state_names, scheduler, simulator):
        super(Agent, self).__init__(state_names, scheduler, simulator)
        self._parent = None

    def _getDependentWCs(self):
        return self._scheduler.l2g_graph[self._curr_channel] if self._is_modified else ()

    def _rescheduleFromWorld(self, world):
        # reschedule world-dependent local channels
        scheduler = self._scheduler
        if world._is_modified:
            for channel in scheduler.g2l_graph[world._curr_channel]:
                scheduler[channel] = channel.scheduleEvent(self, world, scheduler.clock, world)

    def _synchronize(self, tbarrier):
        """
        This should mimic a channel firing a set of nested channels with t0=clock and tf=tbarrier.
        Sync channels are fired with the same initial time:
            Enqueue any cloned agents and process immediately if possible.
        Rescheduling is invoked after each firing:
            Reschedule the sync channel at the event time.
            Reschedule internal dependent channels if entity was changed.
            In FM method, ALSO reschedule dependent world channels if entity was changed.
        The clock is advanced to tbarrier.

        """
        # NOTE: we do not allow sync channels to have other sync channels as dependents!
        scheduler = self._scheduler
        simulator = self._simulator
        world = simulator.world
        # current time
        time = scheduler.clock
        # advance clock to sync barrier
        scheduler.clock = tbarrier
        if scheduler.sync_channels:
            for channel in scheduler.sync_channels:
                # fire channel with t0=time, tf=tbarrier
                self._is_modified = channel.fireEvent(self, world, time, tbarrier)
                self._enqueue_new_agents(channel)
                if isinstance(simulator, FMSimulator):
                    simulator._processAgentQueue()
                # reschedule internal
                scheduler[channel] = channel.scheduleEvent(self, world, scheduler.clock, None)
                if self._is_modified:
                    for dependent in scheduler.dep_graph[channel]:
                        scheduler[dependent] = dependent.scheduleEvent(self, world, scheduler.clock, None)
                # reschedule A2W if is modified
                if isinstance(simulator, FMSimulator) and self._is_modified:
                    world._rescheduleFromAgent(self)

    def __copy__(self):
        """
        Copy the scheduler and the state variables.

        """
        names = self._names
        scheduler = copy(self._scheduler)
        simulator = self._simulator
        other = self.__class__(names, scheduler, simulator)
        for name in names:
            setattr(other, name, copy(getattr(self, name)))
        # The following ugly hack preserves the identity of currently firing channel
        if self._curr_channel is not None:
            other._curr_channel = other._scheduler.channel_dict[self._curr_channel._id]
        return other

    def _kill(self, event_time, remove=True):
        self._scheduler.enabled = False
        if remove:
            q = self._simulator.agent_queue
            q.enqueue(q.DELETE_AGENT, self, event_time)


class LoggedAgent(Agent):
    """
    Agent entity subclass that logs every event to create a lineage tree of
    state and event histories.

    Additional attributes:
        _logger   (cps.logging.LoggerNode)

    """
    def __init__(self, state_names, scheduler, simulator, logger=None):
        super(LoggedAgent, self).__init__(state_names, scheduler, simulator)
        self._logger = logger

    def __copy__(self):
        other = super(LoggedAgent, self).__copy__()
        l_node, r_node = self._logger.branch()
        self._logger = l_node
        other._logger = r_node
        return other

    def _processNextChannel(self):
        super(LoggedAgent, self)._processNextChannel()
        scheduler = self._scheduler
        self._logger.record(scheduler.clock, self._curr_channel._id, self)

    def _fire_nested(self, channel, event_time, reschedule=False, source=None, **kwargs):
        super(LoggedAgent, self)._fire_nested(channel, event_time, reschedule, source, **kwargs)
        scheduler = self._scheduler
        self._logger.record(scheduler.clock, self._curr_channel._id, self)

    # NOTE FOR CLONING EVENTS: the final state of the first new agent
    #   at the completion of the division event gets logged as the first
    #   event on its new logger.
    #
    # The following records the final state of the second agent before it
    # is added to the agent queue
    # def _prepare_new_agent(self, other):
    #     super(LoggedAgent, self)._prepare_new_agent(self, other)
    #     scheduler = other._scheduler
    #     other.logger.record(scheduler.clock, other._curr_channel.id, other)


# user API for agents, world
# def fire(entity, *args, **kwargs):
#     entity._fire(*args, **kwargs)

# def reschedule(entity, *args, **kwargs):
#     entity._resched(*args, **kwargs)

# def clone(agent, *args, **kwargs):
#     agent._clone(*args, **kwargs)

# def kill(agent, *args, **kwargs):
#     agent._kill(*args, **kwargs)