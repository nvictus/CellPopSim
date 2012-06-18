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
    """
    Query and modify simulation entity state.

    """
    def scheduleEvent(self, entity, cargo, time, source):
        """
        Schedule a simulation event.
        Return the putative time of the next event.

        """
        raise NotImplementedError

    def fireEvent(self, entity, cargo, time, event_time, **kwargs):
        """
        Perform a simulation event.
        Return True if the state of the entity was modified, else False.

        """
        raise NotImplementedError

class ILogger(object):
    def record(self, time, world, agents):
        raise NotImplementedError

class IIinitializer(object):
    def initialize(self, world, agents, *args, **kwargs):
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
    def runSimulation(self, tstop):
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

    def __copy__(self):
        raise NotImplementedError

    def _kill(self):
        raise NotImplementedError



#-----------------------------------------------------------------------------
# Internal API used by simulator

class IExecWorld(object):   
    def _scheduleAllChannels(self, agents):
        raise NotImplementedError

    def _fireNextChannel(self, agents): #needs source?
        raise NotImplementedError

    def _crossScheduleL2G(self, agents, dependent_wcs, source_agent=None):
        raise NotImplementedError


class IExecAgent(object):
    def _scheduleAllChannels(self, world):
        raise NotImplementedError

    def _fireNextChannel(self, world): #needs source?
        raise NotImplementedError

    def _synchronize(self, world, tbarrier):
        raise NotImplementedError

    def _getDependentWCs(self):
        raise NotImplementedError

    def _crossScheduleG2L(self, world):
        raise NotImplementedError
    
    #def _prepareNewAgent(self, world):

