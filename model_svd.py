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

from cps import *
from copy import copy
import random
import math
import time

DEBUG = 0

#-------------------------------------------------------------------------------
# STOCHASTICS-VOLUME-DIVISON MODEL
#---------------------------------

class GillespieChannel(AgentChannel):
    """ Performs Gillespie SSA """
    def __init__(self, propensity_fcn, stoich_list):
        self.propensity_fcn = propensity_fcn
        self.stoich_list = stoich_list
        self.tau = None
        self.mu = None

    def scheduleEvent(self, cell, gdata, time, src): #keyword!
        a = self.propensity_fcn(cell.x, gdata)
        a0 = sum(a)
        self.tau = -math.log(random.uniform(0,1))/a0
        r0 = random.uniform(0,1)*a0
        self.mu = 0; s = a[0]
        while s <= r0:
            self.mu += 1
            s += a[self.mu]
        return time + self.tau

    def fireEvent(self, cell, gdata, time, event_time):
        self.fire(cell, 'VolumeChannel')
        for i in range(0, len(cell.x)):
            cell.x[i] += self.stoich_list[self.mu][i]
        return True

class VolumeChannel(AgentChannel):
    """ Increments cell volume """
    def __init__(self, tstep):
        self.tstep = tstep

    def scheduleEvent(self, cell, gdata, time, src):
        return time + self.tstep

    def fireEvent(self, cell, gdata, time, event_time):
        cell.v *= math.exp(gdata.kV*(event_time-time))
        return True

class DivisionChannel(AgentChannel):
    """ Performs cell division and partitioning """
    def __init__(self, prob):
        self.prob = prob

    def scheduleEvent(self, cell, gdata, time, src):
        return time + math.log(cell.v_thresh/cell.v)/gdata.kV

    def fireEvent(self, cell, gdata, time, event_time):
        self.fire(cell,'VolumeChannel')
        new_cell = self.cloneAgent(cell)
        v_mother = cell.v
        cell.v, new_cell.v = self.prob*v_mother, (1-self.prob)*v_mother
        cell.v_thresh = 2 + random.normalvariate(0, 0.15)
        new_cell.v_thresh = 2 + random.normalvariate(0, 0.15)
        x_mother = cell.x[:]
        cell.x[0], new_cell.x[0] = self._binomialPartition(x_mother[0])
        cell.x[1], new_cell.x[1] = self._binomialPartition(x_mother[1])
        return True

    def _binomialPartition(self, n):
        heads = (random.randint(0,1) for j in range(n))
        num_heads = sum( (j for j in heads if j) )
        num_tails = n - num_heads
        return num_heads, num_tails


def my_init(gdata, cells):
    gdata.kR = 0.01
    gdata.kP = 1
    gdata.gR = 0.1
    gdata.gP = 0.002
    gdata.kV = 0.0002
    for cell in cells:
        cell.x = [0, 0]
        cell.v = math.exp(random.uniform(0,math.log(2)))
        cell.v_thresh = 2
        #cell.t_last = 0

def my_logger(log, time, agent):
    log['x0'].append(agent.x[0])
    log['x1'].append(agent.x[1])
    log['v'].append(agent.v)

def my_recorder(log, time, world, agents):
    log['x0'].append([agent.x[0] for agent in agents])
    log['x1'].append([agent.x[1] for agent in agents])
    log['v'].append([agent.v for agent in agents])

def prop_fcn(x, p):
    return [ p.kR,
             p.kP*x[0],
             p.gR*x[0],
             p.gP*x[1] ]

s = (( 1, 0 ),
     ( 0, 1 ),
     (-1, 0 ),
     ( 0,-1 ))

recorder = Recorder([], ['x0','x1','v'], my_recorder)
rc = RecordingChannel(tstep=50, recorder=recorder)
gc = GillespieChannel(propensity_fcn=prop_fcn, stoich_list=s)
vc = VolumeChannel(tstep=5)
dc = DivisionChannel(prob=0.5)

model = Model(n0=100, nmax=100)
model.addInitializer(['kP','kR','gP','gR','kV'], ['x','v','v_thresh'], my_init) #t_last
model.addLogger(0, ['x0','x1','v'], my_logger)
model.addRecorder(recorder)
model.addWorldChannel(channel=rc,
                      ac_dependents=[],
                      wc_dependents=[])
model.addAgentChannel(channel=gc,
                      ac_dependents=[],
                      wc_dependents=[])
model.addAgentChannel(channel=vc,
                      ac_dependents=[],
                      wc_dependents=[],
                      sync=True)
model.addAgentChannel(channel=dc,
                      ac_dependents=[gc,vc],
                      wc_dependents=[])


if __name__=='__main__':
    sim = FMSimulator(model, 0)
    #sim = AMSimulator(model, 0)

    t0 = time.time()
    sim.runSimulation(10000)
    t = time.time()
    print(t-t0)
    recorder = sim.recorders[0]
    logger = sim.loggers[0]

    savemat_snapshot('data/svd2_data.mat', recorder)
    #savemat_lineage('data/svd_lineage.hdf5', logger)




