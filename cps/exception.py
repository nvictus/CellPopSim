"""
Name:        exception

Author:      Nezar Abdennur <nabdennur@gmail.com>
Created:     23/04/2012
Copyright:   (c) Nezar Abdennur 2012

"""
#!/usr/bin/env python

class SimulationError(Exception):
    """
    Base class for exceptions in this module.

    """
    pass

class ZeroPopulationError(SimulationError):
    pass

class LoggingError(SimulationError):
    pass

class TimingError(SimulationError):
    pass

class SchedulingError(TimingError):
    """
    Raise if an event was scheduled to occur at a time preceding the entity's
    current clock time.

    """
    pass
##    def __init__(self, *args):
##        self.channel, self.clock_time, self.sched_time = args
##
##    def __str__(self):
##        return str(self.channel.id) + " attempted to schedule an event at t=" + str(self.sched_time)\
##               + ", but the agent's clock is currently at t=" + str(self.clock_time) + "."

class FiringError(TimingError):
    """
    Raise if user attempts to fire a channel at a time preceding the entity's
    current clock time.

    """
    pass
##    def __init__(self, *args):
##        self.channel, self.clock_time, self.fire_time = args
##
##    def __str__(self):
##        return "Cannot fire an event in the past! " + \
##               str(self.channel.id) + " attempted to fire an event at t=" + str(self.fire_time)\
##               + ", but the agent's clock is currently at t=" + str(self.clock_time) + "."

