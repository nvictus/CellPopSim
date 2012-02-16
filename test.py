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

from channels import *
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

    def snapshot(gdata, cells, time):
        self.x1.append([copy(cell.x[0]) for cell in cells])
        self.x2.append([copy(cell.x[1]) for cell in cells])
        self.v.append([copy(cell.v) for cell in cells])
        self.t.append(time)

class RecordingChannel(GlobalChannel):
    """ Global channel that records population snapshots """
    def __init__(self, tstep, recorder=None):
        self.tstep = tstep
        self.count = 0
        if recorder is None:
            self.recorder = Recorder()
        else:
            self.recorder = recorder

    def scheduleEvent(self, gdata, cells, time):
        if time == 0:
            return time #initial snapshot
        else:
            return time + self.tstep

    def fireEvent(self, gdata, cells, time, event_time):
        self.recorder.snapshot(gdata, cells, event_time)
        self.count += 1
        return False

    def getRecorder(self):
        return self.recorder

class GillespieChannel(LocalChannel):
    """ Performs Gillespie SSA """
    def __init__(self, propensity_fcn, stoich_list):
        self.propensity_fcn = propensity_fcn
        self.stoich_list = stoich_list
        self.tau = None
        self.mu = None

    def scheduleEvent(self, cell, gdata, time):
        a = self.propensity_fcn(cell.x, cell.p)
        a0 = sum(a)
        self.tau = -math.log(random.uniform(0,1))/a0
        s = a[0]; r0 = random.uniform(0,1)*a0
        self.mu = 0
        while s <= r0:
            self.mu += 1
            s += a[self.mu]
        return time + self.tau

    def fireEvent(self, cell, gdata, time, event_time):
        for i in range(0, len(cell.x)):
            cell.x[i] += self.stoich_list[self.mu][i]
        return True

class VolumeChannel(LocalChannel):
    """ Increments cell volume """
    def __init__(self, tstep):
        self.tstep = tstep

    def scheduleEvent(self, cell, gdata, time):
        return time + self.tstep

    def fireEvent(self, cell, gdata, time, event_time):
        cell.v *= math.exp(gdata.kV*(event_time-time))
        return True

class DivisionChannel(LocalChannel):
    """ Performs cell division and partitioning """
    def __init__(self, prob):
        self.prob = prob

    def scheduleEvent(self, cell, gdata, time):
        return time + math.exp(cell.v_thresh/cell.v)/gdata.kV

    def fireEvent(self, cell, gdata, time, event_time):
        new_cell = cell.copy()
        v_mother = cell.v
        cell.v, new_cell.v = self.prob*v_mother, (1-self.prob)*v_mother
        cell.v_thresh = 2 + random.normalvariate(0, 0.05)
        new_cell.v_thresh = 2 + random.normalvariate(0, 0.05)
        x_mother = cell.x
        cell.x[0], new_cell.x[0] = self._binomialPartition(x_mother[0])
        cell.x[1], new_cell.x[1] = self._binomialPartition(x_mother[1])
        self.addEntity(new_cell)
        return True

    def _binomialPartition(self, x):
        heads = (random.randint(0,1) for j in range(x))
        num_heads = sum( (j for j in heads if j) )
        num_tails = x - num_heads
        return num_heads, num_tails

class Model(object):
    def __init__(self, global_channels, global_dg, local_channels, local_dg, init_fcn):
        self.init_num_cells = 10
        self.max_num_cells = 20
        self.global_vars = ('p')
        self.global_channels = global_channels
        self.global_dg = global_dg
        self.local_vars = ('x', 'v', 'v_thresh')
        self.local_channels = local_channels
        self.local_dg = local_dg
        self.init_fcn = init_fcn


from managers import FEMethodManager

def main():

    def initialize(cells, gdata):
        # initialize simulation entities
        gdata.p = {'kR':0.1,
                   'kP':0.1,
                   'gR':0.1,
                   'gP':0.002,
                   'kV':0.015}
        for cell in cells:
            cells.x = [0, 0]
            cells.v = math.exp(random.uniform(0,math.log(2)))
            cells.v_thresh = 2 + random.normalvariate(0,0.05)

    s = (( 1, 0 ),
         ( 0, 1 ),
         (-1, 0 ),
         ( 0,-1 ))

    def prop_fcn(x, p):
        return [ p['kR'],
                 p['kP']*x[0],
                 p['gR']*x[0],
                 p['gP']*x[1] ]

    gchan = RecordingChannel(50)
    chan1 = GillespieChannel(prop_fcn, s)
    chan2 = VolumeChannel(5)
    chan3 = DivisionChannel(0.5)
    model = Model(global_channels=[gchan],
                  global_dg=[(gchan)],
                  local_channels=[chan1,chan2,chan3],
                  local_dg=[(chan1), (chan2), (chan3,chan1,chan2)],
                  init_fcn=initialize)
    FEMethodManager(model, 0)
    FEMethodManager.runSimulation(500)
    sd = gchan.getRecorder()
    print()

if __name__ == '__main__':
    main()
