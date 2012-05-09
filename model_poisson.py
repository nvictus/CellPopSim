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
import math
import random
import time


class PoissonProcessChannel(AgentChannel):
    def __init__(self, lambd):
        self.rate = lambd

    def scheduleEvent(self, cell, world, time, src):
        return time - math.log(random.uniform(0,1))/self.rate

    def fireEvent(self, cell, world, time, event_time, queue):
        cell.state.count += 1
        return True

class PoissonBirthChannel(AgentChannel):
    def __init__(self, lambd):
        self.rate = lambd

    def scheduleEvent(self, cell, world, time, src):
        return time - math.log(random.uniform(0,1))/self.rate

    def fireEvent(self, cell, world, time, event_time, queue):
        cell.state.div_count += 1
        queue.enqueue(queue.ADD_AGENT, cell.clone(), event_time)
        return True

class PoissonDeathChannel(AgentChannel):
    def __init__(self, lambd):
        self.rate = lambd

    def scheduleEvent(self, cell, world, time, src):
        return time - math.log(random.uniform(0,1))/self.rate

    def fireEvent(self, cell, world, time, event_time, queue):
        cell.state.dead = True
        queue.enqueue(queue.DELETE_AGENT, cell, event_time)
        return True

class SyncChannel(WorldChannel):
    def scheduleEvent(self, world, cells, time, src):
        return time + 10

    def fireEvent(self, world, cells, time, event_time, q):
        return False


def initfcn(cells, world, p):
    for cell in cells:
        cell.state.count = 0
        cell.state.div_count = 0
        cell.state.dead = False



if __name__=='__main__':
    model = Model(init_num_agents=10, max_num_agents=1000,
                  agent_vars=('count','div_count','dead'), world_vars=(),
                  initializer=initfcn)

    c1 = PoissonProcessChannel(0.2)
    c2 = PoissonBirthChannel(0.01)
    c3 = PoissonDeathChannel(0.002)
    w1 = SyncChannel()

    model.addWorldChannel(w1)
    model.addAgentChannel(c1)
    model.addAgentChannel(c2)
    model.addAgentChannel(c3)

    sim = AsyncMethodSimulator(model, 0)
    t0 = time.time()
    sim.runSimulation(10000)
    t = time.time()

    print(t-t0)
    print(sim.num_agents)
    print(sim.theoretical_size)



