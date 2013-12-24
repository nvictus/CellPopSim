#-------------------------------------------------------------------------------
# STRESS MODEL
#-------------
#!/usr/bin/env python

from cps import *
import math, random, time

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
        self.e0 = 1 #math.exp(0.25*self.c*self.tau)

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
            cell.fitness = gdata.fmin if cell.y < gdata.Kw else gdata.fmax
            #w = (cell.y/gdata.Kw)**gdata.nw
            #cell.fitness = (gdata.fmax+gdata.fmin*w)/(1 + w)
        else:
            cell.fitness = gdata.fmax
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

if __name__=='__main__':
    from os import path
    DATA_PATH = path.join(path.abspath(path.pardir), 'data')

    for tau in [1.338]:
        # Create model...
        ncrit = 1000
        model = Model(n0=ncrit, nmax=ncrit)

        def my_logger(log, time, agent):
            log['alive'].append(agent.alive)
            log['x'].append(agent.x)
            log['y'].append(agent.y)
            log['capacity'].append(agent.capacity)
        #model.addLogger(0, ['alive','x','y','capacity'], my_logger)

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
            gdata.stress = False
            gdata.Kw = 2 #6 #2.57 #0.5
            gdata.nw = 100
            gdata.fmax = 1 #math.log(2) #if log(2), fastest doubling time = 1
            gdata.fmin = -1# -math.log(2) # if -log(2), fastest death time from neutrality is 1
            for cell in cells:
                cell.alive = True
                cell.x = math.sqrt(0.5*10*0.1)*random.normalvariate(0,1)
                cell.y = math.exp(cell.x)
                cell.capacity = math.exp(random.uniform(0,math.log(2.0)))
        model.addInitializer(['stress', 'Kw', 'nw'], ['alive', 'capacity', 'x', 'y'], initialize)

        rc = RecordingChannel(tstep=0.1, recorder=recorder)
        sc = StressChannel(switch_times=[5])
        #tau = 0.1
        pc = OUProteinChannel(tstep=0.015, tau=tau, c=1/tau)
        dc = DivDeathChannel()
        model.addWorldChannel(channel=rc)
        model.addWorldChannel(channel=sc, ac_dependents=[pc,dc])
        model.addAgentChannel(channel=pc, ac_dependents=[dc], sync=False)
        model.addAgentChannel(channel=dc, ac_dependents=[pc])




        #sim = FMSimulator(model, 0)
        sim = AMSimulator(model, 0)

        t0 = time.time()
        sim.runSimulation(20)
        t = time.time()
        print(t-t0)
        print(sim.nbirths, sim.ndeaths)


        filename = path.join(DATA_PATH, 'stress0_T' + str(tau) + '.mat')
        savemat_snapshot(filename, sim.recorders[0])
        #savemat_lineage('data/stress_lineage.mat', sim.loggers[0])
        #savehdf_lineage('data/test2.hdf5', root)

        #from matplotlib import pyplot as plt
        t = sim.world._ts
        s = sim.world._size
        #plt.plot(t,[si/ncrit for si in s],'-*')
        #plt.show()
        import scipy.io
        scipy.io.savemat(path.join(DATA_PATH, 'stress0p_T' + str(tau) + '.mat'), {'t':t, 'size':s}, oned_as='column')

        #import pickle
        #pickle.dump(recorder, 'tmp1.p')
        #pickle.dump(N, 'tmp2.p')