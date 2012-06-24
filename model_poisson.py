#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      Nezar
#
# Created:     08/05/2012
# Copyright:   (c) Nezar 2012
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python

from cps import *
import math, random, time

class PoissonProcessChannel(AgentChannel):
    def __init__(self, lambd):
        self.rate = lambd

    def scheduleEvent(self, cell, world, time, src):
        return time - math.log(random.uniform(0,1))/self.rate

    def fireEvent(self, cell, world, time, event_time):
        cell.count += 1
        return True

class PoissonBirthChannel(AgentChannel):
    def __init__(self, lambd):
        self.rate = lambd

    def scheduleEvent(self, cell, world, time, src):
        return time - math.log(random.uniform(0,1))/self.rate

    def fireEvent(self, cell, world, time, event_time):
        cell.div_count += 1
        self.cloneAgent(cell)
        return True

class PoissonDeathChannel(AgentChannel):
    def __init__(self, lambd):
        self.rate = lambd

    def scheduleEvent(self, cell, world, time, src):
        return time - math.log(random.uniform(0,1))/self.rate

    def fireEvent(self, cell, world, time, event_time):
        cell.dead = True
        self.killAgent(cell, remove=False)
        return True

class SyncChannel(WorldChannel):
    def scheduleEvent(self, world, cells, time, src):
        return time + 10

    def fireEvent(self, world, cells, time, event_time):
        return False


model = Model(n0=10, nmax=100)
def initfcn(world, cells):
    for cell in cells:
        cell.count = 0
        cell.div_count = 0
        cell.dead = False
model.addInitializer([], ['count','div_count','dead'], initfcn)
c1 = PoissonProcessChannel(0.2)
c2 = PoissonBirthChannel(0.01)
c3 = PoissonDeathChannel(0.002)
w1 = SyncChannel()
model.addWorldChannel(w1)
model.addAgentChannel(c1)
model.addAgentChannel(c2, ac_dependents=[c3])
model.addAgentChannel(c3)

if __name__=='__main__':
    sim = FMSimulator(model, 0)
    #sim = AMSimulator(model, 0)
    t0 = time.time()
    sim.runSimulation(10000)
    t = time.time()

    print(t-t0)
    print(sim.num_agents)



