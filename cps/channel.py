"""
Name:        channel

Author:      Nezar Abdennur <nabdennur@gmail.com>
Created:     02/05/2012
Copyright:   (c) Nezar Abdennur 2012

"""
#!/usr/bin/env python

class AgentChannel(object):
    """
    Base class for agent simulation channels.

    """
    def scheduleEvent(self, agent, world, time, source=None):
        # return putative time of next event
        return float('inf')

    def fireEvent(self, agent, world, time, event_time, queue):
        # return boolean specifying if entity was modified
        return False


class WorldChannel(object):
    """
    Base class for global simulation channels.

    """
    def scheduleEvent(self, world, agents, time, source=None):
        # return event time
        return float('inf')

    def fireEvent(self, world, agents, time, event_time, queue):
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

    def scheduleEvent(self, world, agents, time, src):
        return time + self.tstep

    def fireEvent(self, world, agents, time, event_time, queue):
        self.recorder.record(event_time, world, agents)
        self.count += 1
        return False

    def getRecorder(self):
        return self.recorder
