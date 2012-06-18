"""
Name:        channel

Author:      Nezar Abdennur <nabdennur@gmail.com>
Created:     02/05/2012
Copyright:   (c) Nezar Abdennur 2012

"""
#!/usr/bin/env python

class SimulationChannel(object):
    def __new__(type_, *args, **kwargs):
        self = object.__new__(type_, *args, **kwargs)
        self._id = self.__class__.__name__
        self._new_agents = []
        return self

    def scheduleEvent(self, entity, cargo, time, source=None):
        # return putative time of next event
        raise NotImplementedError

    def fireEvent(self, entity, cargo, time, event_time, **kwargs):
        # return boolean specifying if entity was modified
        raise NotImplementedError

    def fire(self, entity, channel_name, reschedule=False, **kwargs):
        # "manually" fire a specified channel on a given entity
        channel = entity._scheduler.channel_dict[channel_name]
        return entity._fire_nested(channel, self._event_time, reschedule=False, **kwargs)

    def reschedule(self, entity, channel_name, source=None):
        # "manually" reschedule a specified channel of a given entity
        channel = entity._scheduler.channel_dict[channel_name]
        return entity._resched(channel, self._event_time, source)

    def cloneAgent(self, agent):
        new_agent = agent.__copy__()
        new_agent._parent = agent
        self._new_agents.append(new_agent)
        return new_agent

    def killAgent(self, agent, remove=True):
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
    Base class for global simulation channels.

    """
    def scheduleEvent(self, world, agents, time, source=None):
        # return event time
        return float('inf')

    def fireEvent(self, world, agents, time, event_time, **kwargs):
        # return boolean
        return False


class RecordingChannel(WorldChannel):
    """
    World channel that records population snapshots.

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
