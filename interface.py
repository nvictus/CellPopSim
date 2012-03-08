#-------------------------------------------------------------------------------
# Name:        interfaces
# Purpose:
#
# Author:      Nezar
#
# Created:     28/02/2012
# Copyright:   (c) Nezar 2012
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python

class IChannel(object):
    """
    Query and modify simulation entity state.

    """
    def scheduleEvent(self, entity, cargo, time, source):
        raise(NotImplementedError)

    def fireEvent(self, entity, cargo, time, event_time, add_queue, rem_queue):
        raise(NotImplementedError)

class IWorld(object):
    def fireChannel(self, name, cargo, aq, rq):
        raise(NotImplementedError)

    def start(self):
        raise(NotImplementedError)

    def stop(self):
        raise(NotImplementedError)

class IAgent(object):
    def fireChannel(self, name, cargo, aq, rq):
        raise(NotImplementedError)

    def start(self):
        raise(NotImplementedError)

    def stop(self):
        raise(NotImplementedError)

    def clone(self):
        raise(NotImplementedError)

class IRecorder(object):
    """
    Record global simulation data.

    """
    def takeSnapshot(self,time,agents,world,itr):
        raise(NotImplementedError)

class IEngine(object):
    def scheduleAllChannels(self, cargo, source):
        raise(NotImplementedError)

    def fireNextChannel(self, cargo, aq, rq):
        raise(NotImplementedError)

    def rescheduleDependentChannels(self, cargo, source):
        raise(NotImplementedError)

    def closeGaps(self, cargo, aq, rq, source, tbarrier):
        raise(NotImplementedError)

    def rescheduleAux(self, cargo, source):
        raise(NotImplementedError)

    def getNextEventTime(self):
        """ TODO: make this a dependent, read-only property """
        raise(NotImplementedError)