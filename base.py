#-------------------------------------------------------------------------------
# Name:        module2
# Purpose:
#
# Author:      Nezar
#
# Created:     28/02/2012
# Copyright:   (c) Nezar 2012
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python

from interface import *
from misc import DataLogNode
from copy import copy, deepcopy

class SimulationError(Exception):
    """
    Base class for exceptions in this module.

    """
    pass


class SchedulingError(SimulationError):
    """
    Raise if an event was scheduled to occur at a time preceding the entity's
    current clock time.

    """
    def __init__(self, entity, channel, clock_time, sched_time):
        self.entity = entity
        self.channel = channel
        self.clock_time = clock_time
        self.sched_time = sched_time

    def __str__(self):
        return repr(self.channel) + ' ' + \
               'attempted to schedule an event at t=' + str(self.sched_time) + ', ' + \
               'but the agent\'s clock is currently at t=' + str(self.clock_time) + '.'


class AgentChannel(object): #implements IChannel
    """
    Base class for an agent simulation channel.

    """
    def scheduleEvent(self, agent, world, time, source=None):
        # return putative time of next event
        return float('inf')

    def fireEvent(self, agent, world, time, event_time, add_queue, rem_queue):
        # return boolean specifying if entity was modified
        return False


class WorldChannel(object): #implements IChannel
    """
    Base class for global simulation channel.

    """
    def scheduleEvent(self, world, agents, time, source=None):
        # return event time
        return float('inf')

    def fireEvent(self, world, agents, time, event_time, add_queue, rem_queue):
        # return boolean
        return False


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


class Scheduler(object):
    def __init__(self, time, channel_index, gap_channels, dep_graph, l2g_graph=None, g2l_graph=None):
        self.channels = channel_index
        self.gap_channels = gap_channels
        self.dep_graph = dep_graph
        self.l_to_g_graph = l2g_graph
        self.g_to_l_graph = g2l_graph
        self.is_modified = False
        self.timetable = {channel:time for channel in channel_index.values()}

    def __copy__(self):
        # make a copy of each simulation channel, mapped to the original
        map_copied = {channel:copy(channel) for channel in self.timetable}

        # mirror the dict of channels
        channels = {name:map_copied[self.channels[name]] for name in self.channels}

        # mirror the list of gap channels
        gap_channels = [map_copied[gap_channel] for gap_channel in self.gap_channels]

        # mirror the dependency graphs
        dep_graph = {}
        for orig_channel in map_copied:
            dependencies = self.dep_graph[orig_channel]
            dep_graph[map_copied[orig_channel]] = tuple([map_copied[dependency] for dependency in dependencies])
        l_to_g = {}
        for orig_channel in map_copied:
            dependencies = self.l_to_g_graph[orig_channel]
            l_to_g[map_copied[orig_channel]] = tuple([dependency for dependency in dependencies])
        g_to_l = {}
        for world_channel in self.g_to_l_graph:
            dependencies = self.g_to_l_graph[world_channel]
            g_to_l[world_channel] = tuple([map_copied[dependency] for dependency in dependencies])

        # create a new scheduler with cloned channels and dependency graphs
        new_engine = Scheduler(0, channels, gap_channels, dep_graph, l_to_g, g_to_l)
        # copy over the event times
        for channel in self.timetable:
            new_engine.timetable[map_copied[channel]] = self.timetable[channel]

        return new_engine


class Entity(object): #Abstract, extends IScheduler
    """
    Base class for agent/world simulation entities.
    Implements most of the application-side interface.

    """
    def __init__(self, time, state, engine):
        self.clock = time
        self.state = state
        self.engine = engine
        self.is_modified = False
        self._next_channel = None
        self._next_event_time = None
        self._enabled = True

    def scheduleAllChannels(self, cargo, source=None):
        tmin = float('inf')
        cmin = None
        for channel in self.engine.timetable:
            event_time = channel.scheduleEvent(self, cargo, self.clock, source)
            if event_time < self.clock:
                raise SchedulingError(self, channel, self.clock, event_time)
            elif event_time < tmin:
                tmin = event_time
                cmin = channel
            self.engine.timetable[channel] = event_time
        self._next_channel = cmin
        self._next_event_time = tmin
        return tmin

    def fireNextChannel(self, cargo, aq, rq):
        self.is_modified = self._next_channel.fireEvent(self, cargo, self.clock, self._next_event_time, aq, rq)
        self.clock = self._next_event_time
        # reschedule channel that just fired
        last_channel = self._next_channel
        event_time = last_channel.scheduleEvent(self, cargo, self.clock, None)
        if event_time < self.clock:
            raise SchedulingError(self, last_channel, self.clock, event_time)
        self.engine.timetable[last_channel] = event_time

    def rescheduleDependentChannels(self, cargo, source=None):
        if self.is_modified:
            for dependent in self.engine.dep_graph[self._next_channel]:
                event_time = dependent.scheduleEvent(self, cargo, self.clock, source)
                if event_time < self.clock:
                    raise SchedulingError(self, channel, self.clock, event_time)
                self.engine.timetable[dependent] = event_time

    def closeGaps(self, tbarrier, cargo, aq, rq, source=None):
        if self.engine.gap_channels:
            for channel in self.engine.gap_channels:
                is_mod = channel.fireEvent(self, cargo, self.clock, self.clock, aq, rq)
                if is_mod:
                    for dependent in self.engine.dep_graph[channel]:
                        # NOTE:some of these rescheds may be redundant if the dependents
                        # are gap channels that are still pending to fire...
                        event_time = dependent.scheduleEvent(self, cargo, self.clock, source)
                        if event_time < self.clock:
                            raise SchedulingError(self, depedent, self.clock, event_time)
                        self.engine.timetable[dependent] = event_time
        self.clock = tbarrier

    def _getNextEventTime(self):
        """ getter for dependent, read-only property """
        # NOTE:need to compare tmin with ALL channels... or use ipq
        cmin, tmin = min(self.engine.timetable.items(), key=lambda x: x[1])
        self._next_channel = cmin
        self._next_event_time = tmin
        return tmin

    next_event_time = property(fget=_getNextEventTime)

    def rescheduleAux(self, cargo, source):
        raise(NotImplementedError)


class World(Entity): #implements IWorld and IScheduler
    def start(self):
        self._enabled = True

    def stop(self):
        self._enabled = False

    def fireChannel(self, name, cargo, aq, rq):
        channel = self.engine.channels[name]
        t_fire = self.engine._next_event_time
        is_mod = channel.fireEvent(self, cargo, self.clock, t_fire, aq, rq)
        # reschedule channel that just fired
        event_time = channel.scheduleEvent(self, cargo, self.clock, None)
        if event_time < t_fire:
            raise SchedulingError(self, channel, self.clock, event_time)
        self.timetable[channel] = event_time
        # reschedule dependent channels
        if is_mod:
            for dependent in dep_graph[channel]:
                # some of these rescheds may be redundant if the channels
                # are gap channels that have yet to fire...
                event_time = dependent.scheduleEvent(self, cargo, self.clock, None)
                if event_time < self.clock:
                    raise SchedulingError(self, dependent, self.clock, event_time)
                self.timetable[dependent] = event_time

    def rescheduleAux(self, cargo, source_agent):
        """
        Implemented IScheduler interface method.
        Takes as input the agent who fired the offending event.
        Reschedules affected world channels.

        """
        if source_agent.is_modified:
            last_channel = source_agent._next_channel
            for world_channel in source_agent.engine.l_to_g_graph[last_channel]:
                event_time = world_channel.scheduleEvent(self, cargo, self.clock, source_agent)
                if event_time < self.clock:
                    raise SchedulingError(self, world_channel, self.clock, event_time)
                self.engine.timetable[world_channel] = event_time

    def rescheduleAuxAsync(self, cargo, world_channels):
        """
        Different version of rescheduleAux for the Asynchronous Method algorithm.
        This takes the collection of world channels to reschedule as input
        rather than the agents who fired the offending events.

         """
        for world_channel in world_channels:
            event_time = world_channel.scheduleEvent(self, cargo, self.clock, source_agent)
            if event_time < self.clock:
                raise SchedulingError(self, world_channel, self.clock, event_time)
            self.engine.timetable[world_channel] = event_time


class Agent(Entity): #implements IAgent and IScheduler
    def start(self):
        self._enabled = True

    def stop(self):
        self._enabled = False

    def fireChannel(self, name, cargo, aq, rq):
        channel = self.engine.channels[name]
        t_fire = self._next_event_time
        is_mod = channel.fireEvent(self, cargo, self.clock, t_fire, aq, rq)
        # reschedule channel that just fired
        event_time = channel.scheduleEvent(self, cargo, t_fire, None)
        if event_time < t_fire:
            raise SchedulingError(self, channel, t_fire, event_time)
        self.engine.timetable[channel] = event_time
        # reschedule dependent channels
        if is_mod:
            for dependent in self.engine.dep_graph[channel]:
                # some of these rescheds may be redundant if the channels
                # are gap channels that have yet to fire...
                event_time = dependent.scheduleEvent(self, cargo, self.clock, None)
                if event_time < self.clock:
                    raise SchedulingError(self, dependent, self.clock, event_time)
                self.engine.timetable[dependent] = event_time

    def clone(self):
        time = self.clock
        state = copy(self.state)
        engine = copy(self.engine)
        new_agent = Agent(time, state, engine)
        new_agent._next_channel, new_agent._next_event_time = min(new_agent.engine.timetable.items(), key=lambda x: x[1])
        return new_agent

    def rescheduleAux(self, cargo, world):
        """
        Implemented IScheduler interface method.

        """
        if world.is_modified:
            last_channel = world._next_channel
            for agent_channel in self.engine.g_to_l_graph[last_channel]:
                event_time = agent_channel.scheduleEvent(self, cargo, self.clock, world)
                if event_time < self.clock:
                    raise SchedulingError(self, agent_channel, self.clock, event_time)
                self.engine.timetable[agent_channel] = event_time

    def finalizePrevEvent(self, parent):
        # called by agentqueue pop method... TODO:change?
        self.clock = parent._next_event_time
        self.is_modified = parent.is_modified

    def reschedulePrevChannel(self, cargo, source=None):
        # called by main simulation algorithm after agent is popped from queue
        last_channel = self._next_channel
        event_time = last_channel.scheduleEvent(self, cargo, self.clock, source)
        if event_time < self.clock:
            raise SchedulingError(self, last_channel, self.clock, event_time)
        self.engine.timetable[last_channel] = event_time

    def getDependentChannels(self):
        return self.engine.dep_graph[self._next_channel]

    def getDependentWorldChannels(self):
        return self.engine.l_to_g_graph[self._next_channel]


class LineageAgent(Agent):
    def __init__(self, time, state, engine):
        super(LineageAgent, self).__init__(time, state, engine)
        self.node = DataLogNode()

    def fireChannel(self, name, cargo, aq, rq):
        super(LineageAgent, self).fireChannel(name, cargo, aq, rq)
        self.node.record(self.clock, self._next_channel.id, self.state) #TODO: provide id attribute for channels

    def fireNextChannel(self, cargo, aq, rq):
        super(LineageAgent, self).fireNextChannel(cargo, aq, rq)

        # NOTE FOR DIVISION EVENTS: the final state of the first newborn (self)
        #   at the completion of the division event gets logged as the first
        #   event on its new data logger.
        self.node.record(self.clock, self._next_channel.id, self.state)

        # We don't have access to the second newborn here. It should be lying in
        # the agent queue. Its first event is "incomplete" because it doesn't
        # get finalized here.
        # Instead, once it is retrieved from the agent queue, we must record its
        # state to its data logger and advance its clock using finalizePrevEvent
        # below.

    def finalizePrevEvent(self, parent_agent):
        self.clock = parent_agent._next_event_time
        self.is_modified = parent_agent.is_modified
        # log the event that caused division, recording final state of the newborn
        self.node.record(self.clock, self._next_channel.id, self.state)

    def clone(self):
        time = self.clock
        state = copy(self.state)
        engine = copy(self.engine)

        # make new agent, mirror the next-event info of the parent agent
        other = LineageAgent(time, state, engine)
        other._next_channel, other._next_event_time = min(other.engine.timetable.items(), key=lambda x: x[1])

        # branch into two new nodes
        l_node, r_node = self.node.branch()

        self.node = l_node
        other.node = r_node
        return other


class RecordingChannel(WorldChannel):
    """ Global channel that records population snapshots """
    def __init__(self, tstep, recorder=None):
        self.tstep = tstep
        self.count = 0
        if recorder is None:
            raise SimulationError("Must provide a recorder.")
        else:
            self.recorder = recorder

    def scheduleEvent(self, gdata, cells, time, src):
        return time + self.tstep

    def fireEvent(self, gdata, cells, time, event_time, aq, rq):
        self.recorder.snapshot(gdata, cells, event_time)
        self.count += 1
        return False

    def getRecorder(self):
        return self.recorder



import numpy as np
import h5py

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




#-------------------------------------------------------------------------------
def main():
    #s = State(['a','b','c'])
    s = SchedulingError(None, AgentChannel(), 10.0, 8.5)
    print(s)

if __name__ == '__main__':
    main()
