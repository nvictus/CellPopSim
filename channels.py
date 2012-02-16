#-------------------------------------------------------------------------------
# Name:        channels
# Purpose:
#
# Author:      Nezar
#
# Created:     26/01/2012
# Copyright:   (c) Nezar 2012
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python

from base import *
import math
import random

class AgentChannel(Channel):
    """
    Base class for an agent simulation channel.

    """
    def scheduleEvent(self, agent, world, time, source=None):
        # return putative time of next event
        return float('inf')

    def fireEvent(self, agent, world, time, event_time, add_queue, rem_queue):
        # return boolean specifying if entity was modified
        return False

class WorldChannel(Channel):
    """
    Base class for global simulation channel.

    """
    def scheduleEvent(self, world, agents, time, source=None):
        # return event time
        return float('inf')

    def fireEvent(self, world, agents, time, event_time, add_queue, rem_queue):
        # return boolean
        return False


    #def rescheduleOn(channel, doAll=False):
        # create one-time dynamic scheduling dependency
        #pass






class GillespieChannel(AgentChannel):
    """ Performs Gillespie SSA """
    def __init__(self, propensity_fcn, stoich_list):
        self.propensity_fcn = propensity_fcn
        self.stoich_list = stoich_list
        self.tau = None
        self.mu = None

    def scheduleEvent(self, cell, gdata, time, source):
        a = self.propensity_fcn(cell.state.x, gdata.state)
        a0 = sum(a)
        self.tau = -math.log(random.uniform(0,1))/a0
        s = a[0]
        self.mu = 0
        r0 = random.uniform(0,1)*a0
        while s <= r0:
            self.mu += 1
            s += a[self.mu]
        return time + self.tau

    def fireEvent(self, cell, gdata, time, event_time, aq, rq):
        for i in range(0, len(cell.state.x)):
            cell.state.x[i] += self.stoich_list[self.mu][i]
            if cell.state.x < [0, 0]:
                raise Exception
        return True



# Some tests...

#import unittest
from entities import *

def main():
    s = ((1, 0), (0, 1), (-1, 0), (0, -1))
    prop_fcn = lambda x, p: [ p.kR, p.kP*x[0], p.gR*x[0], p.gP*x[1] ]
    channel = GillespieChannel(propensity_fcn=prop_fcn, stoich_list=s)

    cell = Agent(State( ('x',) ), None)
    cell.state.x = [0, 0]
    gdata = World(State( ('kR','kP','gR','gP') ), None)
    gdata.state.kR = 0.1
    gdata.state.kP = 0.1
    gdata.state.gR = 0.1
    gdata.state.gP = 0.002

    tstop = 100
    t = [0.0]
    x = [tuple(cell.state.x)]
    while t[-1] < tstop:
        ev_time = channel.scheduleEvent(cell, gdata, t[-1], None)
        is_mod = channel.fireEvent(cell, gdata, t[-1], ev_time, [], [])
        t.append(ev_time)
        x.append(tuple(cell.state.x))
    for i in range(len(x)):
        print(t[i],'\t',x[i])

if __name__ == '__main__':
    main()
