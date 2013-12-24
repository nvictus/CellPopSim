"""
Name:        channel

Author:      Nezar Abdennur <nabdennur@gmail.com>
Created:     02/05/2012
Copyright:   (c) Nezar Abdennur 2012

"""

class SimulationChannel(object):
    """
    Simulation channels are the principal abstraction of this framework.
    Subclasses must implement scheduleEvent() and fireEvent().

    """
    def __new__(type_, *args, **kwargs):
        self = object.__new__(type_, *args, **kwargs)
        self._id = self.__class__.__name__
        self._new_agents = []
        return self

    def scheduleEvent(self, entity, cargo, time, source=None):
        """
        Schedule this channel.
        Return the putative time of the next event of this type

        """
        raise NotImplementedError

    def fireEvent(self, entity, cargo, time, event_time, **kwargs):
        """
        Fire this channel.
        Perform the event. This may modify the entity.
        Return True if the entity was modified in order to invoke
        rescheduling of dependent channels, else return False.

        """
        # return boolean specifying if entity was modified
        raise NotImplementedError

    def fire(self, entity, channel_name, reschedule=False, **kwargs):
        """
        "Manual" channel firing (nested firing).
        Fires the specified channel on the provided entity.
        Raises key error if the entity does not possess the channel.
        Optional named arguments can be passed to the channel.
        If reschedule option is true:
            The clock of the provided entity is advanced to the event time
            of this channel.
            The channel is rescheduled.
            Internal dependent channels are rescheduled.
            External ones are not.

        """
        channel = entity._scheduler.channel_dict[channel_name]
        return entity._fireNested(channel, self._event_time, reschedule=False, **kwargs)

    def reschedule(self, entity, channel_name, source=None):
        """
        "Manual" channel rescheduling.
        Reschedules the specified channel on the provided entity.
        No rescheduling on dependent channels.
        Raises key error if the entity does not possess the channel.

        """
        channel = entity._scheduler.channel_dict[channel_name]
        return entity._resched(channel, self._event_time, source)

    def cloneAgent(self, agent):
        """
        Returns a new agent with the same state as the one provided.

        """
        new_agent = agent.__copy__()
        new_agent._parent = agent
        self._new_agents.append(new_agent)
        return new_agent

    def killAgent(self, agent, remove=True):
        """
        Cease simulation of an agent after this channel finishes firing.
        If remove option is True, the agent is permanently removed 
        from the population.

        """
        agent._kill(self._event_time, remove)


class AgentChannel(SimulationChannel):
    """
    Base class for agent simulation channels.

    """
    def scheduleEvent(self, agent, world, time, source=None):
        # return putative time of next event
        return float('inf')

    def fireEvent(self, agent, world, time, event_time, **kwargs):
        # return boolean specifying if entity was modified
        return False

class WorldChannel(SimulationChannel):
    """
    Base class for world simulation channels.

    """
    def scheduleEvent(self, world, agents, time, source=None):
        # return event time
        return float('inf')

    def fireEvent(self, world, agents, time, event_time, **kwargs):
        # return boolean
        return False


class RecordingChannel(WorldChannel):
    """
    World channel that records population snapshots at fixed
    time intervals.

    """
    def __init__(self, tstep, recorder):
        self.tstep = tstep
        self.recorder = recorder
        self.count = 0

    def scheduleEvent(self, world, agents, time, source):
        return time + self.tstep

    def fireEvent(self, world, agents, time, event_time):
        self.recorder.record(event_time, world, agents)
        self.count += 1
        return False
