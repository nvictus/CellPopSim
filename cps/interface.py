"""
Name:        interface

Interface classes for main components of the simulation framework. These
interfaces only serve as documentation since python doesn't enforce them.
(Note: could use ABC's to do that.)

Author:      Nezar Abdennur <nabdennur@gmail.com>
Created:     28/02/2012
Copyright:   (c) Nezar Abdennur 2012

"""
#!/usr/bin/env python

class IChannel(object):
    """
    Query and modify simulation entity state.

    """
    def scheduleEvent(self, entity, cargo, time, source):
        """
        Schedule a simulation event.
        Return the putative time of the next event.

        """
        raise NotImplementedError

    def fireEvent(self, entity, cargo, time, event_time, queue):
        """
        Perform a simulation event.
        Return True if the state of the entity was modified, else False.

        """
        raise NotImplementedError


class IWorld(object):
    """
    User-side interface provided by a world entity.
    Simulation entities encapsulate state and a scheduler.
    A world entity holds common resources and global variables.

    """
    def fireChannel(self, name, cargo, event_time, q):
        """
        Perform simulation event of named channel.
        The simulation clock is not advanced.

        """
        raise NotImplementedError

    def start(self):
        """
        Promote the entity into the event loop.

        """
        raise NotImplementedError

    def stop(self):
        """
        Remove the entity from the event loop.

        """
        raise NotImplementedError


class IAgent(object):
    """
    User-side interface provided by an agent entity.
    Simulation entities encapsulate state and a scheduler.
    An agent entity holds the state of an individual. Agents can be replicated.

    """
    def fireChannel(self, name, cargo, event_time, q):
        """
        Perform simulation event of named channel.
        The simulation clock is not advanced.

        """
        raise NotImplementedError

    def start(self):
        """
        Promote the agent into the event loop.

        """
        raise NotImplementedError

    def stop(self):
        """
        Remove the agent from the event loop.

        """
        raise NotImplementedError

    def clone(self):
        """
        Make a new agent that is a copy of the current one.

        """
        raise NotImplementedError


class IScheduler(object):
    """
    Application-side interface provided by a simulation entity (agent/world).
    This interface is used by the simulation manager to conduct a simulation.

    """
    def scheduleAllChannels(self, cargo, source):
        """
        Schedule every simulation channel and store event times in a timetable.

        """
        raise NotImplementedError

    def fireNextChannel(self, cargo, q):
        """
        Fire the simulation channel with the earliest event time.
        Advance the simulation clock.
        Reschedule the channel.

        """
        raise NotImplementedError

    def rescheduleDependentChannels(self, cargo, source):
        """
        Reschedule channels that depend on the previously fired channel.

        """
        raise NotImplementedError

    def closeGaps(self, cargo, q, source, tbarrier):
        """
        Fire gap simulation channels with event time 'tbarrier'.
        Reschedule any dependent channels.
        Advance clock to tbarrier.

        """
        raise NotImplementedError

    def rescheduleAux(self, cargo, source):
        """
        Reschedule any channels that depend on the last channel fired by the
        foreign entity 'source'.

        """
        raise NotImplementedError

    def getNextEventTime(self):
        """ TODO: make this a dependent, read-only property """
        raise NotImplementedError


class IRecorder(object):
    """
    Record global simulation data.

    """
    def record(self, time, world, agents):
        raise NotImplementedError