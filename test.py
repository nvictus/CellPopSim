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

from base import AgentChannel, WorldChannel
import random
import math
from copy import copy

from managers import FEMethodManager, AsyncMethodManager, Model
import time
import numpy as np
import h5py

DEBUG = 0

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


#-------------------------------------------------------------------------------
# STOCHASTICS-VOLUME-DIVISON MODEL
#---------------------------------
class SVDModelRecorder(object):
    """ Saves population snapshots """
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

    def _binomialPartition(self, n):
        heads = (random.randint(0,1) for j in range(n))
        num_heads = sum( (j for j in heads if j) )
        num_tails = n - num_heads
        return num_heads, num_tails

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

    rc = RecordingChannel(50, recorder=SVDModelRecorder())
    gc = GillespieChannel(prop_fcn, s)
    vc = VolumeChannel(5)
    dc = DivisionChannel(0.5)

    rc.name = 'RecordingChannel'
    gc.name = 'GillespieChannel'
    vc.name = 'VolumeChannel'
    dc.name = 'DivisionChannel'

    def initialize(cells, gdata, p):
        # initialize simulation entities
        gdata.state.p = {'kR':0.01,
                         'kP':1,
                         'gR':0.1,
                         'gP':0.002,
                         'kV':0.0002}
        for cell in cells:
            cell.state.x = [0, 0]
            cell.state.v = math.exp(random.uniform(0,math.log(2)))
            cell.state.v_thresh = 2
            cell.state.t_last = 0

    def my_logger(state):
        return [state.x[0],state.x[1],state.v]

    model = Model(init_num_agents=2,
                  max_num_agents=100,
                  world_vars=('p'),
                  agent_vars=('x', 'v', 'v_thresh', 't_last'),
                  init_fcn=initialize,
                  logger=my_logger,
                  track_lineage=[0],
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
    root = mgr.root_nodes[0]

    # record lineage data...
    def traverse(node, adj_list=[]):
        if node is not None:
            adj_list.append([node.parent, node])
            traverse(node.lchild, adj_list)
            traverse(node.rchild, adj_list)
        return adj_list

    node_list = traverse(root)
    data = []
    ts = []
    es = []
    adj_list = []
    row = 0
    for parent, child in node_list:
        ts.extend([meta[0] for meta in child.meta])
        es.extend([meta[1] for meta in child.meta])
        data.extend(child.log)
        pid = id(parent) if parent is not None else 0
        cid = id(child)
        adj_list.append([pid, cid, row, len(child.log)])
        row += len(child.log)

    try:
        dfile = h5py.File('lineage.hdf5','w')
        dfile.create_dataset(name='adj_list_info',
                             data=np.array(['parent_id', 'id', 'start_row', 'num_events'], dtype=np.bytes_))
        dfile.create_dataset(name='adj_list',
                             data=np.array(adj_list))

        dfile.create_dataset(name='node_data_info',
                             data=np.array(['x1','x2','v'], dtype=np.bytes_))
        dfile.create_dataset(name='node_data',
                             data=np.array(data))

        dfile.create_dataset(name='timestamp',
                             data=np.array(ts))
        dfile.create_dataset(name='eventstamp',
                             data=np.array(es, dtype=np.bytes_))
    finally:
        dfile.close()







#-------------------------------------------------------------------------------
# STRESS MODEL
#-------------
class StressModelRecorder(object):
    """ Saves population snapshots """
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

class StressChannel(WorldChannel):
    """ Turn stress on or off. """
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

    def fireEvent(self, gdata, cells, time, event_time, aq, rq):
        gdata.state.stress = not(gdata.state.stress)
        return True

class OUProteinChannel(AgentChannel):
    """ Protein expression modeled as a geometric Ornstein-Uhlenbeck process. """
    def __init__(self, tstep, tau, c):
        self.tau = tau
        self.c = c
        self.tstep = tstep
        self.e0 = math.exp(0.25*self.c*self.tau)
        self.fmax = math.log(2) #min doubling time = 1
        self.fmin = -0.04*math.log(2)

    def scheduleEvent(self, cell, gdata, time, src):
        return time + self.tstep

    def fireEvent(self, cell, gdata, time, event_time, aq, rq):
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

    def fireEvent(self, cell, gdata, time, event_time, aq, rq):
        if self.event_flag == 1:
            new_cell = cell.clone()
            cell.state.capacity = 1.0
            new_cell.state.capacity = 1.0
            aq.addAgent(cell, new_cell, event_time)
            #global DEBUG
            #DEBUG += 1
            #print(DEBUG)
            return True
        elif self.event_flag == 2:
            cell.state.alive = False
            cell._enabled = False
            #print('dead!')
            return False
        else:
            return False


def main2():
    rc = RecordingChannel(tstep=0.5, recorder=StressModelRecorder())
    sc = StressChannel(switch_times=[40.0])
    pc = OUProteinChannel(tstep=0.01, tau=10.0, c=1/10)
    dc = DivDeathChannel()

    def initialize(cells, gdata, data):
        # initialize simulation entities
        gdata.state.stress = False
        gdata.state.Kw = 0.1
        gdata.state.nw = 10
        for cell in cells:
            cell.state.alive = True
            cell.state.x = math.sqrt(0.5*10*0.1)*random.normalvariate(0,1)
            cell.state.y = math.exp(random.uniform(0,1)*math.log(2.0))
            cell.state.capacity = math.exp(random.uniform(0,math.log(2.0)))

    model = Model(init_num_agents=100,
                  max_num_agents=100,
                  world_vars=('stress', 'Kw', 'nw'),
                  agent_vars=('x', 'y', 'capacity','alive'),
                  init_fcn=initialize,
                  parameters=[])

    model.addWorldChannel(channel=rc,
                          name='W1',
                          is_gap=False,
                          ac_dependents=[],
                          wc_dependents=[])
    model.addWorldChannel(channel=sc,
                          name='W2',
                          is_gap=False,
                          ac_dependents=[pc, dc],
                          wc_dependents=[])
    model.addAgentChannel(channel=pc,
                          name='A1',
                          is_gap=False,
                          ac_dependents=[dc],
                          wc_dependents=[])
    model.addAgentChannel(channel=dc,
                          name='A2',
                          is_gap=False,
                          ac_dependents=[pc],
                          wc_dependents=[])

    mgr = AsyncMethodManager(model, 0)


    t0 = time.time()
    mgr.runSimulation(80)
    t = time.time()
    print(t-t0)


    sd = rc.getRecorder()
    dfile = h5py.File('stress_data.hdf5', 'w')
    dset1 = dfile.create_dataset(name='time', data=np.array(sd.t))
    dset2 = dfile.create_dataset(name='stress', data=np.array(sd.stress))
    dset3 = dfile.create_dataset(name='alive', data=np.array(sd.alive))
    dset4 = dfile.create_dataset(name='x', data=np.array(sd.x))
    dset5 = dfile.create_dataset(name='y', data=np.array(sd.y))
    dset6 = dfile.create_dataset(name='capacity', data=np.array(sd.capacity))
    dfile.close()



#-------------------------------------------------------------------------------
if __name__ == '__main__':
    main()
