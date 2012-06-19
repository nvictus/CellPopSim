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

#---------------------------------------------------------------------------------
# Framework API

class IChannel(object):
    def scheduleEvent(self, entity, cargo, time, source):
        raise NotImplementedError

    def fireEvent(self, entity, cargo, time, event_time, **kwargs):
        raise NotImplementedError

class ILogger(object):
    def record(self, time, entity):
        raise NotImplementedError

class IRecorder(object):
    def record(self, time, world, agents):
        raise NotImplementedError

class IModel(object):
    def addAgentChannel(self):
        raise NotImplementedError

    def addWorldChannel(self):
        raise NotImplementedError

    def addInitializer(self):
        raise NotImplementedError

    def addLogger(self):
        raise NotImplementedError

    def addRecorder(self):
        raise NotImplementedError

class ISimulator(object):
    def initialize(self):
        raise NotImplementedError

    def runSimulation(self, tstop):
        raise NotImplementedError

    def finalize(self):
        raise NotImplementedError


#-----------------------------------------------------------------------------
# Internal API used by channel

class IWorld(object):
    """
    User-side interface provided by a world entity.
    Simulation entities encapsulate state and a scheduler.
    A world entity holds common resources and global variables.

    """
    def _fireNested(self, channel_name, firing_time, source=None, **kwargs):
        raise NotImplementedError

    def _reschedule(self, channel_name, source=None):
        raise NotImplementedError

    def _stop(self):
        raise NotImplementedError

class IAgent(object):
    """
    User-side interface provided by an agent entity.
    Simulation entities encapsulate state and a scheduler.
    An agent entity holds the state of an individual. Agents can be replicated.

    """
    def _fireNested(self, channel_name, firing_time, source=None, **kwargs):
        raise NotImplementedError

    def _reschedule(self, channel_name, source=None):
        raise NotImplementedError

    def _stop(self):
        raise NotImplementedError

    def __copy__(self):
        raise NotImplementedError

    def _kill(self):
        raise NotImplementedError


#-----------------------------------------------------------------------------
# Internal API used by simulator

class IExecWorld(object):   
    def _scheduleAllChannels(self):
        raise NotImplementedError

    def _processNextChannel(self): #needs source?
        raise NotImplementedError

    def _rescheduleFromAgent(self, source_agent=None):
        raise NotImplementedError


class IExecAgent(object):
    def _scheduleAllChannels(self):
        raise NotImplementedError

    def _processNextChannel(self): #needs source?
        raise NotImplementedError

    def _synchronize(self, tbarrier):
        raise NotImplementedError

    def _rescheduleFromWorld(self, world):
        raise NotImplementedError
    
    #def _prepareNewAgent(self, world):

