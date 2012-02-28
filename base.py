#-------------------------------------------------------------------------------
# Name:        base
# Purpose:
#
# Author:      Nezar
#
# Created:     11/01/2012
# Copyright:   (c) Nezar 2012
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python


# Exception classes
class Error(Exception):
    """
    Base class for exceptions in this module.

    """
    pass


class SchedulingError(Error):
    def __init__(self, entity, channel, clock_time, sched_time):
        self.entity = entity
        self.channel = channel
        self.clock_time = clock_time
        self.sched_time = sched_time
#-------------------------------------------------------------------------------

# Interfaces
class IChannel(object):
    """
    Query and modify simulation entity state.

    """
    def scheduleEvent(self, entity, cargo, time, source):
        raise(NotImplementedError)

    def fireEvent(self, entity, cargo, time, event_time, add_queue, rem_queue):
        raise(NotImplementedError)


class IManager(object):
    """
    Operate the entities (world and agents) which make up a simulation.

    """
    def _createWorld(self, t0, state_variables, channels, dep_graph):
        raise(NotImplementedError)

    def _createAgents(self, num_agents, t0, state_variables, channels, dep_graph):
        raise(NotImplementedError)

    def initialize(self):
        raise(NotImplementedError)

    def runSimulation(self):
        raise(NotImplementedError)


class IRecorder(object):
    """
    Record global simulation data.

    """
    def takeSnapshot(self,time,agents,world,itr):
        raise(NotImplementedError)
#-------------------------------------------------------------------------------


class SimData(object):
    """
    Store simulation run information.

    """
    def __init__(self):
        self.t_elapsed = None
        self.date_stamp = None
        self.version = None
        self.model = None
        self.recorders = [] #snapshot and/or lineage


class State(object):
    """
    Contain the state variables of an entity.

    """
    def __init__(self, var_names):
        for var_name in var_names:
            setattr(self, var_name, None)


class IEngine(object):
    """
    Should expose:
        list of channels
        gap channels
        local dependency graph
        local-to-global dependencies
        global-to-local dependencies

    Should hide:
        clock
        timetable

    """
    def scheduleAllChannels(self, cargo, source):
        """ Return next event time. """
        pass

    def rescheduleDependents(self, cargo, source):
        pass

    def fireNextChannel(self, cargo, aq, rq):
        """ Fire, advance clock, reschedule, and reschedule dependents, returns bool. """
        pass

    def closeGaps(self, cargo, aq, rq):
        pass

    def getNextEventTime(self):
        pass



class Engine(object):
    """
    Generic class. Manage the simulation channels of an entity.
    Attributes:
        clock (double): current simulation time
        channels (dict): maps name to channel
        timetable (dict): maps channel to its event time
        dep_graph (dict): maps channel to its dependencies
        gap_channels (list): subset of channels specified as being 'gap channels'

    """
    def scheduleAllChannels(self, entity, cargo, source):
        """
        Returns the earliest event time.

        """
        tmin = float('inf')
        cmin = None
        for channel in self.timetable:
            event_time = channel.scheduleEvent(entity, cargo, self.clock, source)
            if event_time < self.clock:
                raise SchedulingError(entity, channel, self.clock, event_time)
            elif event_time < tmin:
                tmin = event_time
                cmin = channel
            self.timetable[channel] = event_time

        self._next_channel = cmin
        self._next_event_time = tmin
        return tmin

    def rescheduleChannels(self, entity, cargo, source):
        """
        Reschedules the last channel that fired and if the entity's state was
        modified, reschedules all dependent channels as well.

        """
        for channel in self.dep_graph[self._next_channel]:
            event_time = channel.scheduleEvent(entity, cargo, self.clock, source)
            if event_time < self.clock:
                raise SchedulingError(entity, channel, self.clock, event_time)
            self.timetable[channel] = event_time

    def _rescheduleDependents(self, entity, cargo, source, last_channel):
        """ TODO:Maybe get rid of this....
        Reschedules the specified channel that fired and if the entity's state
        was modified, reschedules all dependent channels as well.

        """
        for channel in self.dep_graph[last_channel]:
            event_time = channel.scheduleEvent(entity, cargo, self.clock, source)
            if event_time < self.clock:
                raise SchedulingError(entity, channel, self.clock, event_time)
            self.timetable[channel] = event_time

    def getNextEventTime(self):
        """
        Returns the earliest event time.

        """
        # NOTE:need to compare tmin with ALL channels... or use ipq
        cmin, tmin = min(self.timetable.items(), key=lambda x: x[1])
        self._next_channel = cmin
        self._next_event_time = tmin
        return tmin

    def fireNextChannel(self, entity, cargo, aq, rq):
        """
        Executes the channel with the earliest event time, advances clock, then
        reschedules the channel that fired.

        """
        # fire event
        self._is_modified = self._next_channel.fireEvent(entity, cargo, self.clock, self._next_event_time, aq, rq)
        last_channel = self._next_channel
        # advance clock
        self.clock = self._next_event_time
        # TODO:if lineage cell, append this event to history log of current cell

        # reschedule channel that just fired
        event_time = last_channel.scheduleEvent(entity, cargo, self.clock, source)
        if event_time < self.clock:
            raise SchedulingError(entity, last_channel, self.clock, event_time)
        self.timetable[last_channel] = event_time

        # reschedule dependent channels
        if self._is_modified:
            for dependent in self.dep_graph[last_channel]:
                    event_time = dependent.scheduleEvent(entity, cargo, self.clock, source)
                    if event_time < self.clock:
                        raise SchedulingError(entity, channel, self.clock, event_time)
                    self.timetable[dependent] = event_time

    def closeGaps(self, tbarrier, entity, cargo, aq, rq, source):
        """
        Fire gap channels and invoke rescheduling dependencies if either exist.
        Advance clock to time barrier.

        """
        if self.gap_channels:
            for channel in self.gap_channels:
                is_mod = channel.fireEvent(entity, cargo, self.clock, self.clock, aq, rq)
                if is_mod:
                    for dependent in dep_graph[channel]:
                        # some of these rescheds may be redundant if the channels
                        # are gap channels that have yet to fire...
                        event_time = dependent.scheduleEvent(entity, cargo, self.clock, source)
                        if event_time < self.clock:
                            raise SchedulingError(entity, depedent, self.clock, event_time)
                        self.timetable[dependent] = event_time
        self.clock = tbarrier

    def fireChannel(self, name, entity, cargo, aq, rq):
        """
        Fire arbitrary simulation channel specified by name. Do not advance the clock.

        """
        return self.channels[name].fireEvent(entity, cargo, self.clock, self.clock, aq, rq)






#-------------------------------------------------------------------------------
def main():
    pass

if __name__ == '__main__':
    main()
