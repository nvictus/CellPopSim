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

from base import AgentChannel, WorldChannel, RecordingChannel, save_lineage, save_snapshot
import random
import math
from copy import copy

from managers import FEMethodManager, AsyncMethodManager, Model
import time
import numpy as np
import h5py

DEBUG = 0

#-------------------------------------------------------------------------------
#TODO: make a generic recorder
class Recorder(object):
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


class SpaceChannel(AgentChannel):
    def __init__(self, n, n0):
        self.grid = np.zeros([n, n])
        for i in np.random.randint(n*n, size=n0):
            self.grid.flat[i] = 1.0

    def scheduleEvent(self, cell, gdata, time, src):
        """ Move an agent """
        pass

    def fireEvent(self, cell, gdata, time, event_time, aq, rq):
        """ Move an agent """
        return True

class ResolveCollisionChannel(WorldChannel):
    """ Resolve collision somehow """
    def __init__(self):
        pass

    def scheduleEvent(self, cell, gdata, time, src):
        pass

    def fireEvent(self, cell, gdata, time, event_time, aq, rq):
        return True

class MoveChannel(AgentChannel):
    """ Check for collision, trigger handler """
    def __init__(self):
        pass

    def scheduleEvent(self, cell, gdata, time, src):
        pass

    def fireEvent(self, cell, gdata, time, event_time, aq, rq):
        return True

class ChangeStateChannel(AgentChannel):
    def __init__(self):
        pass

    def scheduleEvent(self, cell, world, time, src):
        pass

    def fireEvent(self, cell, world, time, event_time, aq, rq):
        pass

class CtsVarChannel(AgentChannel):
    def __init__(self):
        pass






def main():
    pass


#-------------------------------------------------------------------------------
if __name__ == '__main__':
    main()
