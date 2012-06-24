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
import math, random, time
#import pickle

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

    def fireEvent(self, gdata, cells, time, event_time):
        gdata.stress = not(gdata.stress)
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

    def fireEvent(self, cell, gdata, time, event_time):
        # update protein expression
        mu = math.exp(-self.tstep/self.tau)
        sig = math.sqrt((self.c*self.tau/2)*(1-mu**2))
        cell.x *= mu
        cell.x += sig*(random.normalvariate(0,1))
        cell.y = math.exp(cell.x)/self.e0

        # compute reproductive rate and update reproductive capacity
        if gdata.stress:
            w = (cell.y/gdata.Kw)**gdata.nw
            cell.fitness = (self.fmax+self.fmin*w)/(1 + w)
        else:
            cell.fitness = self.fmax
        cell.capacity *= math.exp(cell.fitness*self.tstep)
        return True

class DivDeathChannel(AgentChannel):
    """
    Cell divides if reproductive capacity exceeds upper threshold.
    Cell dies if reproductive capacity falls below lower threshold.

    """
    def __init__(self):
        self.event_flag = None

    def scheduleEvent(self, cell, gdata, time, src):
        if cell.capacity > 2:
            self.event_flag = 1
            return time
        elif cell.capacity < 0.5:
            self.event_flag = 2
            return time
        else:
            return float('inf')

    def fireEvent(self, cell, gdata, time, event_time):
        if self.event_flag == 1:
            new_cell = self.cloneAgent(cell)
            cell.capacity = 1.0
            new_cell.capacity = 1.0
            return True
        elif self.event_flag == 2:
            cell.alive = False
            self.killAgent(cell, remove=True)
            return True
        else:
            raise SimulationError


# Create model...
model = Model(n0=1, nmax=100)

def my_logger(log, time, agent):
    log['alive'].append(agent.alive)
    log['x'].append(agent.x)
    log['y'].append(agent.y)
    log['capacity'].append(agent.capacity)
model.addLogger(0, ['alive','x','y','capacity'], my_logger)

def my_recorder(log, time, world, agents):
    log['stress'].append(world.stress)
    log['alive'].append([agent.alive for agent in agents])
    log['capacity'].append([agent.capacity for agent in agents])
    log['x'].append([agent.x for agent in agents])
    log['y'].append([agent.y for agent in agents])
recorder = Recorder(['stress'], ['alive','x','y','capacity'], my_recorder)
model.addRecorder(recorder)

def initialize(gdata, cells):
    # initialize simulation entities
    gdata.critical_size = 1
    gdata.stress = False
    gdata.Kw = 0.5
    gdata.nw = 10
    for cell in cells:
        cell.alive = True
        cell.x = math.sqrt(0.5*10*0.1)*random.normalvariate(0,1)
        cell.y = math.exp(random.uniform(0,1)*math.log(2.0))
        cell.capacity = math.exp(random.uniform(0,math.log(2.0)))
model.addInitializer(['stress', 'Kw', 'nw'], ['alive', 'capacity', 'x', 'y'], initialize)

rc = RecordingChannel(tstep=0.5, recorder=recorder)
sc = StressChannel(switch_times=[40])
pc = OUProteinChannel(tstep=0.1, tau=10, c=0.1)
dc = DivDeathChannel()
model.addWorldChannel(channel=rc)
model.addWorldChannel(channel=sc, ac_dependents=[pc,dc])
model.addAgentChannel(channel=pc, ac_dependents=[dc], sync=False)
model.addAgentChannel(channel=dc, ac_dependents=[pc])


if __name__=='__main__':
    sim = FMSimulator(model, 0)
    #sim = AMSimulator(model, 0)

    t0 = time.time()
    sim.runSimulation(80)
    t = time.time()
    print(t-t0)
    print(sim.nbirths, sim.ndeaths)

    savemat_snapshot('data/stress.mat', sim.recorders[0])
    savemat_lineage('data/stress_lineage.mat', sim.loggers[0])
    #savehdf_lineage('data/test2.hdf5', root)


##    # pickle
##    save_file = open('data/stress_model.p','wb')
##    pickle.dump(recorder, save_file)
##    save_file.close()