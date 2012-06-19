#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      Nezar
#
# Created:     19/03/2012
# Copyright:   (c) Nezar 2012
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python

from cps import *
from cps.exception import *
from copy import copy
import math, random, time
import pickle

#-------------------------------------------------------------------------------
# STRESS MODEL
#-------------

class StressChannel(WorldChannel):
    """
    Turn external stressor on or off.

    """
    def __init__(self, switch_times):
        self.switch_times = switch_times
        self.count = 0

    def scheduleEvent(self, gdata, cells, time, src):
        if self.count >= len(self.switch_times):
            event_time = float('inf')
        else:
            event_time = self.switch_times[self.count]
            self.count += 1
        return event_time

    def fireEvent(self, gdata, cells, time, event_time, q):
        gdata.state.stress = not(gdata.state.stress)
        return True

class OUProteinChannel(AgentChannel):
    """
    Protein expression modeled as a geometric Ornstein-Uhlenbeck process.

    """
    def __init__(self, tstep, tau, c):
        self.tau = tau
        self.c = c
        self.tstep = tstep
        self.e0 = math.exp(0.25*self.c*self.tau)
        self.fmax = 0.5*math.log(2) #min doubling time = 1
        self.fmin = -0.75*math.log(2)

    def scheduleEvent(self, cell, gdata, time, src):
        return time + self.tstep

    def fireEvent(self, cell, gdata, time, event_time, q):
        # update protein expression
        mu = math.exp(-self.tstep/self.tau)
        sig = math.sqrt((self.c*self.tau/2)*(1-mu**2))
        cell.state.x *= mu
        cell.state.x += sig*(random.normalvariate(0,1))
        cell.state.y = math.exp(cell.state.x)/self.e0

        # compute reproductive rate and update reproductive capacity
        if gdata.state.stress:
            w = (cell.state.y/gdata.state.Kw)**gdata.state.nw
            cell.state.fitness = (self.fmax+self.fmin*w)/(1 + w)
        else:
            cell.state.fitness = self.fmax
        cell.state.capacity *= math.exp(cell.state.fitness*self.tstep)
        return True

class DivDeathChannel(AgentChannel):
    """
    Cell divides if reproductive capacity exceeds upper threshold.
    Cell dies if reproductive capacity falls below lower threshold.

    """
    def __init__(self):
        self.event_flag = None

    def scheduleEvent(self, cell, gdata, time, src):
        if cell.state.capacity > 2:
            self.event_flag = 1
            return time
        elif cell.state.capacity < 0.5:
            self.event_flag = 2
            return time
        else:
            return float('inf')

    def fireEvent(self, cell, gdata, time, event_time, q):
        if self.event_flag == 1:
            new_cell = cell.clone()
            cell.state.capacity = 1.0
            new_cell.state.capacity = 1.0
            q.enqueue(q.ADD_AGENT, new_cell, event_time)
            return True
        elif self.event_flag == 2:
            cell.state.alive = False
            q.enqueue(q.DELETE_AGENT, cell, event_time)
            return True
        else:
            raise SimulationError


class StressModelRecorder(object):
    """
    Saves population snapshots.

    """
    from copy import copy
    def __init__(self):
        self.t = []
        self.stress = []
        self.alive = []
        self.x = []
        self.y = []
        self.capacity = []

    def snapshot(self, gdata, cells, time):
        self.t.append(time)
        self.stress.append(gdata.state.stress)
        self.alive.append([copy(cell.state.alive) for cell in cells])
        self.x.append([copy(cell.state.x) for cell in cells])
        self.y.append([copy(cell.state.y) for cell in cells])
        self.capacity.append([copy(cell.state.capacity) for cell in cells])

def initialize(gdata, cells):
    # initialize simulation entities
    gdata.critical_size = 1
    gdata.state.stress = False
    gdata.state.Kw = 0.5
    gdata.state.nw = 10
    for cell in cells:
        cell.state.alive = True
        cell.state.x = math.sqrt(0.5*10*0.1)*random.normalvariate(0,1)
        cell.state.y = math.exp(random.uniform(0,1)*math.log(2.0))
        cell.state.capacity = math.exp(random.uniform(0,math.log(2.0)))

def my_logger(state):
    return [state.alive, state.x, state.y, state.capacity]

rec = Recorder(['stress', 'Kw', 'nw'],['x', 'y', 'capacity','alive'])
rc = RecordingChannel(tstep=0.5, recorder=rec)
sc = StressChannel(switch_times=[40])
pc = OUProteinChannel(tstep=0.01, tau=10, c=0.1)
dc = DivDeathChannel()

model = Model(init_num_agents=1, max_num_agents=100)
model.addInitializer(['stress','Kw','nw'], ['x', 'y', 'capacity', 'alive'], initialize)
model.addLogger(0, ['alive','x','y','capacity'], my_logger)
model.addRecorder(rec)
model.addWorldChannel(channel=rc,
                      name='RecordingChannel',
                      ac_dependents=[],
                      wc_dependents=[])
model.addWorldChannel(channel=sc,
                      name='StressChannel',
                      ac_dependents=[pc, dc],
                      wc_dependents=[])
model.addAgentChannel(channel=pc,
                      name='Expression+Capacity',
                      sync=False,
                      ac_dependents=[dc],
                      wc_dependents=[])
model.addAgentChannel(channel=dc,
                      name='DivisionChannel',
                      sync=False,
                      ac_dependents=[pc],
                      wc_dependents=[])




if __name__=='__main__':
    #sim = FEMethodSimulator(model, 0)
    sim = AsyncMethodSimulator(model, 0)

    t0 = time.time()
    sim.runSimulation(80)
    t = time.time()
    print(t-t0)
    print(sim.nbirths, sim.ndeaths)

    savemat_snapshot('data/test.mat', rec)
    savemat_lineage('data/test2.mat', sim.loggers[0])
    #savehdf_lineage('data/test2.hdf5', root)

    #save_snapshot('data/stress_data_tau10.hdf5',sd)
    #save_lineage('data/stress_lineage.hdf5', root, ['alive','x','y','capacity'])

    #save_file = open('data/stress_model.p','wb')
    #pickle.dump(sd, save_file)
    #save_file.close()