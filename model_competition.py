#-------------------------------------------------------------------------------
# COMPETITION MODEL
#------------------
#!/usr/bin/env python

from cps import *
import math, random, time

ncrit = 1000

class ResourceChannel(WorldChannel):
    def scheduleEvent(self, world, cells, time, src):
        return float('inf')

    def fireEvent(self, world, cells, time, event_time, dR, dt):
        # update global pool of resource
        Nvirtual = world._size[-1]
        Nmax = ncrit
        world.R += -(1/world.V)*dR*(Nvirtual/Nmax) + k_dil*(1-world.R)*dt #R_supplied = 1
        return True

class DiffusionChannel(AgentChannel):
    def scheduleEvent(self, cell, world, time, src):
        return float('inf')

    def fireEvent(self, cell, world, time, event_time):
        # do diffusion for one cell and consume some resources
        grad = world.R-cell.R
        dt = event_time-time
        cell.R += ( (1/cell.V)*cell.k_diff*grad - cell.k_deg*cell.R )*dt
        self.fire(world, 'ResourceChannel', dR=cell.k_diff*grad*dt, dt=dt )
        return True

class CellDivisionChannel(AgentChannel):
    def __init__(self, lambd):
        self.lambd = lambd

    def scheduleEvent(self, cell, world, time, src):
        # predict value of internal resource at time barrier
        cell.R_Barrier = cell.R + ((1/cell.V)*cell.k_diff*(world.R-cell.R) - cell.k_deg*cell.R)*(cell.t_Barrier-time)
        # find tau by linear approx method
        a0 = self.lambd*cell.R
        aB = self.lambd*cell.R_Barrier
        alpha = (aB-a0)/(cell.t_Barrier-time)
        r = random.uniform(0,1)
        if alpha != 0:
            try:
                tau = a0/alpha*(-1 + math.sqrt(1-(2*alpha*math.log(r)/a0**2)))
            except(ValueError, ZeroDivisionError): #FIXME: ZeroDiv error is strange...
                tau = float('inf')
        else:
            tau = -math.log(r)/a0
        return time + tau

    def fireEvent(self, cell, world, time, event_time):
        self.fire(cell, 'DiffusionChannel')
        cell.div_count += 1
        new_cell = self.cloneAgent(cell)
        return True

class CellDeathChannel(AgentChannel):
    def __init__(self, death_rate):
        self.death_rate = death_rate

    def scheduleEvent(self, cell, world, time, src):
        r = random.uniform(0,1)
        return time - math.log(r)/self.death_rate

    def fireEvent(self, cell, world, time, event_time):
        self.fire(cell, 'DiffusionChannel')
        cell.death_count +=1
        self.killAgent(cell)
        return True


class CellDilutionChannel(WorldChannel):
    def scheduleEvent(self, world, agents, time, src):
        r = random.uniform(0,1)
        Nvirtual = world._size[-1]
        dil_rate = world.k_dil*Nvirtual
        return time - math.log(r)/dil_rate

    def fireEvent(self, world, agents, time, event_time):
        Nmax = ncrit
        Nvirtual = world._size[-1]
        # pretend a random cell got diluted away...
        # no need to actually remove one!
        world._size.append(Nvirtual-1)
        world._ts.append(event_time)
        return False

##class CellDilutionChannel(AgentChannel):
##    def scheduleEvent(self, cell, world, time, src):
##        r = random.uniform(0,1)
##        return time - math.log(r)/world.k_dil
##
##    def fireEvent(self, cell, world, time, event_time):
##        self.fire(cell, 'DiffusionChannel')
##        Nmax = ncrit
##        Nvirtual = world._size[-1]
##        # pretend a random cell got diluted away...
##        # no need to actually remove one!
##        world._size.append(Nvirtual-Nvirtual/Nmax)
##        world._ts.append(event_time)
##        return False


class BarrierStepChannel(AgentChannel):
    def __init__(self, dTB):
        self.dTB = dTB

    def scheduleEvent(self, cell, world, time, src):
        return cell.t_Barrier

    def fireEvent(self, cell, world, time, event_time):
        self.fire(cell, 'DiffusionChannel')
        cell.t_Barrier = event_time + self.dTB
        return True


# Create the model...

model = Model(n0=ncrit, nmax=ncrit)


rec_step = 0.01

R_ext = 1
V_ext = 1
V_int = 1e-4
k_diff = 0.01
k_deg = 0.05
k_dil = 0.01

barrier_len = 0.5
div_rate = 0.1
death_rate = 0.02

def my_init(world, cells):
    world.R = R_ext
    world.V = V_ext
    world.k_dil = k_dil
    for cell in cells:
        cell.k_diff = k_diff
        cell.k_deg = k_deg
        cell.V = V_int
        cell.R = 0.5*random.uniform(0,1)
        cell.t_Barrier = cell._time + barrier_len
        cell.R_Barrier = ((1/cell.V)*cell.k_diff*(world.R-cell.R) - cell.k_deg*cell.R)*(cell.t_Barrier-cell._time)
        cell.div_count = 0
        cell.death_count = 0
model.addInitializer(['R', 'k_dil'], ['R', 'R_Barrier', 't_Barrier', 'V', 'k_diff', 'k_deg', 'div_count', 'death_count'], my_init)

##def my_logger(log, time, agent):
##    log['R'].append(agent.R)
##    log['rB'].append(agent.R_Barrier)
##    log['tB'].append(agent.t_Barrier)
##    log['div_count'].append(agent.div_count)
##    log['death_count'].append(agent.death_count)
##model.addLogger(0, ['R','rB','tB','div_count','death_count'], my_logger)

def my_recorder(log, time, world, agents):
    log['Rext'].append(world.R)
    log['Rint'].append([agent.R for agent in agents])
recorder = Recorder(['Rext'], ['Rint'], my_recorder)
model.addRecorder(recorder)

Crec = RecordingChannel(tstep=rec_step, recorder=recorder)
CresW = ResourceChannel()
CresA = DiffusionChannel()
Cdiv = CellDivisionChannel(lambd=div_rate)
Cdeath = CellDeathChannel(death_rate=death_rate)
Cdil = CellDilutionChannel()
Cbar = BarrierStepChannel(dTB=barrier_len)

model.addWorldChannel(channel=Crec)
model.addWorldChannel(channel=CresW )
model.addAgentChannel(channel=CresA, sync=True)
model.addAgentChannel(channel=Cdeath)
model.addAgentChannel(channel=Cdiv, ac_dependents=[Cdeath])
model.addAgentChannel(channel=Cbar, ac_dependents=[Cdiv])

model.addWorldChannel(channel=Cdil)


def main():
    sim = FMSimulator(model, 0)

    t0 = time.time()
    sim.runSimulation(200)
    t = time.time()
    print(t-t0)

    savemat_snapshot('c:/users/nezar/temp/competition-model/snapshot.mat', sim.recorders[0])
    #savemat_lineage('c:/users/nezar/temp/competition-model/lineage.mat', sim.loggers[0])

    import scipy.io
    scipy.io.savemat('c:/users/nezar/temp/competition-model/size.mat', {'t':sim.world._ts, 'sz':sim.world._size}, oned_as='column')

if __name__ == '__main__':
    main()



    #log = sim.recorders[0].log
    #log2 = sim.loggers[0].log
    #from matplotlib import pyplot as plt
    #plt.plot(log['time'], log['Rint'])
    #plt.plot(log['time'], log['Rext'], 'k')
    #plt.plot(log2['time'], log2['R'], 'b')
    #plt.plot(log2['time'], log2['div_count'], 'k')
    #plt.show()