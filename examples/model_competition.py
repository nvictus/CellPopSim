#-------------------------------------------------------------------------------
# COMPETITION MODEL
#------------------
#!/usr/bin/env python
#
#
# Diffusion of a nutrient across a membrane:
# dn/dt = P*A*dC/dx
# where n is the absolute amount of nutrient
#       P is permeability (assume constant), A is the membrane surface area
#       dC/dt is the concentration gradient
#
# If we assume only diffusion between a single cell and the external container:
#   dCcell/dt = (1/Vcell)*P*Acell*(Cexternal-Ccell)             [DIFFUSION TERM {1}]
#   dCexternal/dt  = -(1/Vexternal)*P*Acell*(Cexternal-Ccell)
#
# But since each cell represents Nvirtual/Nmax cells, the actual rate of change
# in the external container is:
#   dCexternal/dt = -(1/Vexternal)*P*Acell*(Cexternal-Ccell)*(Nvirtual/Nmax)    [DIFFUSION TERM {2}]
#
# We're going to assume Vexternal is fixed.
#
#
# Now, let's also consider a steady state external volume with equal flow rates
# in and out. There is a media reservoir of with nutrient concentration C0
# flowing in, and media and cells flowing out.
#
#   dCexternal/dt = [DIFFUSION TERM {2}] + kdil*(C0-Cexternal)
#
# Also, for the cell, let's assume the cell is consuming the nutrient with rate
# kdeg:
#
#   dCcell/dt = [DIFFUSION TERM {1}] - kdeg*Ccell


# IMPORTANT ####################################################################
# NOTE: Right now, I am assuming P*Acell is a constant, kdiff.
#       Technically, this is not correct, as Acell changes with cell volume.
#
#       If we assume spherical cells:
#
#       dCcell/dt = (1/Vcell)*P*Acell*(Cexternal-Ccell)
#       For a sphere, Acell/Vcell = 3/r, so:
#       dCcell/dt = P * (3/r) * (Cexternal-Ccell)
#       where r = cuberoot(3*Vcell/4/pi), so:
#
#       dCcell/dt = P*(3/cuberoot(3*Vcell/4/pi))*(Cexternal-Ccell)    [DIFFUSION TERM {3}]
#
#       For Cexternal we get:
#       Acell = (3/r)*Vcell, where r = cuberoot(3*Vcell/4/pi)
#       so Acell = 3*Vcell/cuberoot(3*Vcell/4/pi)
#       which gives us:
#
#       dCexternal/dt = -(1/Vexternal)*P*(3*Vcell/cuberoot(3*Vcell/4/pi))*(Cexternal-Ccell)*(Nvirtual/Nmax)    [DIFFUSION TERM {4}]
#
#       However, in the model below, all cells have an identical fixed volume,
#       so the expressions with kdiff are valid.


from cps import *
import math, random, time

class ResourceChannel(WorldChannel):
    """
    Updates the world's concentration of resource R due to:
        - diffusion with an agent (Nvirtual/Nmax virtual cells)
        - exchange with a reservoir and sink

    """
    def scheduleEvent(self, world, cells, time, src):
        return float('inf')

    def fireEvent(self, world, cells, time, event_time, gradient, dt):
        Nvirtual = world._size[-1]
        diffusionIn_rate = -(1/Vexternal)*kdiff*gradient*(Nvirtual/Nmax)
        netFlowIn_rate = kdil*(Rreservoir - world.R)

        world.R += (diffusionIn_rate + netFlowIn_rate)*dt
        return True

class DiffusionChannel(AgentChannel):
    """
    Updates a cell's concentration of resource R due to:
        - diffusion with the environment
        - metabolic consumption, degradation

    """
    def scheduleEvent(self, cell, world, time, src):
        return float('inf')

    def fireEvent(self, cell, world, time, event_time):
        gradient = world.R-cell.R
        dt = event_time-time
        diffusionIn_rate = (1/cell.V)*kdiff*gradient
        consumption_rate = kdeg*cell.R

        cell.R += (diffusionIn_rate - consumption_rate)*dt
        self.fire(world, 'ResourceChannel', gradient=gradient, dt=dt)
        return True

class CellDivisionChannel(AgentChannel):
    """
    Performs cell division as a "reaction" whose propensity depends on the
    resource concentration R(t) inside the cell over time. Since the kinetic
    rate depends on time, we use the Shahrezaei and Swain algorithm.

    This involves setting a series of time barriers for providing a linear
    approximation of the division propensity. The position of the next barrier
    is controlled by BarrierStepChannel.

    """
    def __init__(self, div_rate):
        self.div_rate = div_rate

    def scheduleEvent(self, cell, world, time, src):
        # predict value of internal resource at time barrier
        gradient = world.R-cell.R
        dt = cell.TBarrier-time
        diffusionIn_rate = (1/cell.V)*kdiff*gradient
        consumption_rate = kdeg*cell.R
        cell.RBarrier = cell.R + (diffusionIn_rate - consumption_rate)*dt

        # find tau by linear approx method
        a0 = self.div_rate*cell.R # value now
        aB = self.div_rate*cell.RBarrier # value at barrier
        alpha = (aB-a0)/(cell.TBarrier-time) # slope
        r = random.uniform(0,1)
        if alpha == 0:
            # slope is zero, so we have a constant propensity
            tau = -math.log(r)/a0
        else:
            if a0 == 0 or -math.log(r) >= 0.5*a0**2/alpha:
                # our a(t) approximation crosses the t-axis given the r we sampled
                # in this case, we assume the reaction doesn't happen
                tau = float('inf')
            else:
                tau = a0/alpha*(-1 + math.sqrt(1-(2*alpha*math.log(r)/a0**2)))

        return time + tau

    def fireEvent(self, cell, world, time, event_time):
        self.fire(cell, 'DiffusionChannel')
        cell.div_count += 1
        new_cell = self.cloneAgent(cell)
        return True

class BarrierStepChannel(AgentChannel):
    """
    Sets a series of time barriers for improving the prediction of the time of
    cell division by CellDivisionChannel.
    If the next predicted division time is later than the current time barrier,
    this channel will fire first, advancing the agent's clock to the barrier.
    Then CellDivisionChannel will be rescheduled using the next time barrier.

    """
    def __init__(self, barrier_size):
        self.barrier_size = barrier_size

    def scheduleEvent(self, cell, world, time, src):
        return cell.TBarrier

    def fireEvent(self, cell, world, time, event_time):
        self.fire(cell, 'DiffusionChannel')
        cell.TBarrier = event_time + self.barrier_size
        return True


class CellDeathChannel(AgentChannel):
    """
    Cell death is a stochastic reaction with constant rate (i.e. a poisson process).

    """
    def __init__(self, death_rate):
        self.death_rate = death_rate

    def scheduleEvent(self, cell, world, time, src):
        r = random.uniform(0,1)
        return time - math.log(r)/self.death_rate

    def fireEvent(self, cell, world, time, event_time):
        self.fire(cell, 'DiffusionChannel')
        self.killAgent(cell)
        return True


class CellDilutionChannel(WorldChannel):
    """
    Cells are being diluted away with the media. Implemented as a WORLD channel.

    We'll treat it as a stochastic reaction with rate constant kdil. Our
    "reactor" is the whole system, so the reaction propensity would be
    kdil*Nvirtual, where Nvirtual is the virtual population size.

    The effect of the reaction is the loss of ONE virtual cell.
    Since the cell that gets diluted away is random and completely unbiased,
    we don't have to actually have to delete any agents from the collection.
    """
    def scheduleEvent(self, world, agents, time, src):
        r = random.uniform(0,1)
        Nvirtual = world._size[-1]
        dilution_rate = kdil*Nvirtual
        return time - math.log(r)/dilution_rate

    def fireEvent(self, world, agents, time, event_time):
        # NOTE: Sync channels fire before this fires
        Nvirtual = world._size[-1]
        # pretend a random cell got diluted away...
        # no need to actually remove one!
        world._size.append(Nvirtual - 1)
        world._ts.append(event_time)
        return False


class CellDilutionChannel2(AgentChannel):
    """
    Cells are being diluted away with the media. Implemented as an AGENT channel.

    We'll treat it as a poisson process with rate kdil.
    NOTE: This poisson process will be occuring in each agent in the collection simultaneously.

    The effect of the reaction is the death of an agent, which corresponds to
    the loss of Nvirtual/Nmax virtual cells from the virtual population.

    We don't have to actually have to delete the agent from the collection,
    since the dilution event depends in no way on the agent's state and so does
    not affect the composition of the population.

    """
    def scheduleEvent(self, cell, world, time, src):
        r = random.uniform(0,1)
        return time - math.log(r)/kdil

    def fireEvent(self, cell, world, time, event_time):
        self.fire(cell, 'DiffusionChannel')
        Nvirtual = world._size[-1]
        # pretend Nvirtual/Nmax virtual cells got diluted away...
        # no need to actually delete an agent!
        world._size.append(Nvirtual - Nvirtual/Nmax)
        world._ts.append(event_time)
        return False





# Create the model...
Nmax = 100
model = Model(n0=Nmax, nmax=Nmax)

# CONSTANTS
recorder_step = 0.01
barrier_size = 0.5
div_rate = 0.1
death_rate = 0.02
Vexternal = 1
Vcell0 = 1e-4
Rreservoir = 1
kdiff = 0.01
kdeg = 0.05
kdil = 0.01


# Initializer
def my_init(world, cells):
    world.R = Rreservoir
    for cell in cells:
        cell.V = Vcell0
        cell.R = 0.5*random.uniform(0,1)
        cell.TBarrier = cell._time + barrier_size
        cell.RBarrier = ((1/cell.V)*kdiff*(world.R-cell.R) - kdeg*cell.R)*(cell.TBarrier-cell._time)
        cell.div_count = 0
model.addInitializer(['R'], ['V', 'R', 'TBarrier', 'RBarrier', 'div_count'], my_init)


# Recording/logging
def my_recorder(log, time, world, agents):
    log['Rext'].append(world.R)
    log['Rint'].append([agent.R for agent in agents])
recorder = Recorder(['Rext'], ['Rint'], my_recorder)
model.addRecorder(recorder)

##def my_logger(log, time, agent):
##    log['R'].append(agent.R)
##    log['rB'].append(agent.RBarrier)
##    log['tB'].append(agent.TBarrier)
##    log['div_count'].append(agent.div_count)
##model.addLogger(0, ['R','rB','tB','div_count'], my_logger)


# Add the channels
Crec = RecordingChannel(tstep=recorder_step, recorder=recorder)
CresW = ResourceChannel()
CresA = DiffusionChannel()
Cdiv = CellDivisionChannel(div_rate=div_rate)
Cdeath = CellDeathChannel(death_rate=death_rate)
Cdil = CellDilutionChannel()
Cbar = BarrierStepChannel(barrier_size=barrier_size)

model.addWorldChannel(channel=Crec)
model.addWorldChannel(channel=CresW )
model.addWorldChannel(channel=Cdil)

model.addAgentChannel(channel=CresA, sync=True)
model.addAgentChannel(channel=Cdeath)
model.addAgentChannel(channel=Cdiv, ac_dependents=[Cdeath])
model.addAgentChannel(channel=Cbar, ac_dependents=[Cdiv])



from os import path
DATA_PATH = path.join(path.abspath(path.pardir), 'data')
# Run the simulation
if __name__ == '__main__':
    sim = FMSimulator(model, 0)

    t0 = time.time()
    sim.runSimulation(50)
    t = time.time()
    print(t-t0)

    savemat_snapshot(path.join(DATA_PATH, 'snapshot_test.mat'),
        sim.recorders[0])
    #savemat_lineage('c:/users/nezar/temp/competition-model/lineage.mat', sim.loggers[0])

    import scipy.io
    size_data = {'t':sim.world._ts, 'sz':sim.world._size}
    scipy.io.savemat(path.join(DATA_PATH, 'size.mat'), size_data, oned_as='column')

