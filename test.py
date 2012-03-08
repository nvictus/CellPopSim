#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      Nezar
#
# Created:     31/01/2012
# Copyright:   (c) Nezar 2012
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python

from base import *
import random
import math

class Recorder(object):
    """ Saves population snapshots """
    from copy import copy
    def __init__(self):
        self.x1 = []
        self.x2 = []
        self.v = []
        self.t = []

    def snapshot(self, gdata, cells, time):
        self.x1.append([copy(cell.state.x[0]) for cell in cells])
        self.x2.append([copy(cell.state.x[1]) for cell in cells])
        self.v.append([copy(cell.state.v) for cell in cells])
        self.t.append(time)

class RecordingChannel(WorldChannel):
    """ Global channel that records population snapshots """
    def __init__(self, tstep, recorder=None):
        self.tstep = tstep
        self.count = 0
        if recorder is None:
            self.recorder = Recorder()
        else:
            self.recorder = recorder

    def scheduleEvent(self, gdata, cells, time, src):
        return time + self.tstep

    def fireEvent(self, gdata, cells, time, event_time, aq, rq):
        self.recorder.snapshot(gdata, cells, event_time)
        self.count += 1
        return False

    def getRecorder(self):
        return self.recorder

class GillespieChannel(AgentChannel):
    """ Performs Gillespie SSA """
    def __init__(self, propensity_fcn, stoich_list):
        self.propensity_fcn = propensity_fcn
        self.stoich_list = stoich_list
        self.tau = None
        self.mu = None

    def scheduleEvent(self, cell, gdata, time, src):
        a = self.propensity_fcn(cell.state.x, gdata.state.p)
        a0 = sum(a)
        self.tau = -math.log(random.uniform(0,1))/a0

        r0 = random.uniform(0,1)*a0
        self.mu = 0; s = a[0]
        while s <= r0:
            self.mu += 1
            s += a[self.mu]

        return time + self.tau

    def fireEvent(self, cell, gdata, time, event_time, aq, rq):
        for i in range(0, len(cell.state.x)):
            cell.state.x[i] += self.stoich_list[self.mu][i]
        return True

class VolumeChannel(AgentChannel):
    """ Increments cell volume """
    def __init__(self, tstep):
        self.tstep = tstep

    def scheduleEvent(self, cell, gdata, time, src):
        return time + self.tstep

    def fireEvent(self, cell, gdata, time, event_time, aq, rq):
        cell.state.v *= math.exp(gdata.state.p['kV']*(event_time-cell.state.t_last))
        cell.state.t_last = event_time
        return True

class DivisionChannel(AgentChannel):
    """ Performs cell division and partitioning """
    def __init__(self, prob):
        self.prob = prob

    def scheduleEvent(self, cell, gdata, time, src):
        return time + math.log(cell.state.v_thresh/cell.state.v)/gdata.state.p['kV']

    def fireEvent(self, cell, gdata, time, event_time, aq, rq):
        new_cell = cell.clone()
        v_mother = cell.state.v
        cell.state.v, new_cell.state.v = self.prob*v_mother, (1-self.prob)*v_mother
        cell.state.v_thresh = 2 + random.normalvariate(0, 0.05)
        new_cell.state.v_thresh = 2 + random.normalvariate(0, 0.05)
        cell.state.t_last = event_time
        new_cell.state.t_last = event_time
        x_mother = cell.state.x[:]
        cell.state.x[0], new_cell.state.x[0] = self._binomialPartition(x_mother[0])
        cell.state.x[1], new_cell.state.x[1] = self._binomialPartition(x_mother[1])
        aq.addAgent(cell, new_cell, event_time)
        return True

    def _binomialPartition(self, x):
        heads = (random.randint(0,1) for j in range(x))
        num_heads = sum( (j for j in heads if j) )
        num_tails = x - num_heads
        return num_heads, num_tails




#-------------------------------------------------------------------------------
import time
from managers import FEMethodManager, AsyncMethodManager, Model
def main():

    s = (( 1, 0 ),
         ( 0, 1 ),
         (-1, 0 ),
         ( 0,-1 ))

    def prop_fcn(x, p):
        return [ p['kR'],
                 p['kP']*x[0],
                 p['gR']*x[0],
                 p['gP']*x[1] ]

    rc = RecordingChannel(50)
    gc = GillespieChannel(prop_fcn, s)
    vc = VolumeChannel(5)
    dc = DivisionChannel(0.5)

    def initialize(cells, gdata, p):
        # initialize simulation entities
        gdata.state.p = {'kR':0.1,
                         'kP':0.1,
                         'gR':0.1,
                         'gP':0.002,
                         'kV':0.0002}
        for cell in cells:
            cell.state.x = [0, 0]
            cell.state.v = math.exp(random.uniform(0,math.log(2)))
            cell.state.v_thresh = 2
            cell.state.t_last = 0

    model = Model(init_num_agents=100,
                  max_num_agents=100,
                  world_vars=('p'),
                  agent_vars=('x', 'v', 'v_thresh', 't_last'),
                  init_fcn=initialize,
                  parameters=[])

    model.addWorldChannel(channel=rc,
                          name='W1',
                          is_gap=False,
                          ac_dependents=[],
                          wc_dependents=[])
    model.addAgentChannel(channel=gc,
                          name='A1',
                          is_gap=False,
                          ac_dependents=[],
                          wc_dependents=[])
    model.addAgentChannel(channel=vc,
                          name='A2',
                          is_gap=True,
                          ac_dependents=[],
                          wc_dependents=[])
    model.addAgentChannel(channel=dc,
                          name='A3',
                          is_gap=False,
                          ac_dependents=[gc,vc],
                          wc_dependents=[])

    mgr = AsyncMethodManager(model, 0)

    t0 = time.time()
    mgr.runSimulation(10000)
    t = time.time()
    print(t-t0)

    sd = rc.getRecorder()


    print(len(sd.x2[-1]))


#-------------------------------------------------------------------------------
if __name__ == '__main__':
    main()
