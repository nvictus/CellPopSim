"""
Name:        model

Author:      Nezar Abdennur <nabdennur@gmail.com>
Created:     23/04/2012
Copyright:   (c) Nezar Abdennur 2012

"""
#!/usr/bin/env python
import cps.entity
import cps.logging
import cps.misc
from cps.channel import AgentChannel, WorldChannel

import collections
_ChannelEntry = collections.namedtuple('ChannelEntry', 'channel wc_dependents ac_dependents sync')

class Model(object):
    """
    Specify an agent-based model.

    The Model constructor requires the following:
        init_num_agents (int): the initial number of agents to create
        max_num_agents (int): the maximum number of agents allowed

    A functional model also needs:
    *addInitializer() to add a state initializer
        world_vars (list-of-string): names of world state variables
        agent_vars (list-of-string): names of agent state variables
        initializer (callable): a user-defined function to initialize the states
                                of the world and agents

    The next thing to be added are the simulation channels. These require
    information including a qualified name and global and local dependencies:
    *addWorldChannel() to add a world channel
    *addAgentChannel() to add an agent channel

    The following are optional:
    *addLogger() to trace the state and event history of an agent and its descendants
        logger (callable): user-defined function that returns state data to be
                           logged after each event [the default logger records
                           all agent state variables]
    *addRecorder() to record population snapshot data
        recorders (cps.state.Recorder): instance that logs population-scale data

    """
    WorldType = cps.entity.World
    AgentType = cps.entity.Agent
    LoggedAgentType = cps.entity.LoggedAgent
    AgentQueueType = cps.misc.AgentQueue

    def __init__(self, n0, nmax):
        # Required properties
        if n0 > nmax:
            raise ValueError("Must have initial # agents <= maximum # agents.")
        self.n0 = n0
        self.nmax = nmax

        self.world_vars = ()
        self.agent_vars = ()
        self.initializer = lambda x,y: None
        self.world_channel_table = {}
        self.agent_channel_table = {}
        self.logged = {}
        self.recorders = []

    def addInitializer(self, world_varnames, agent_varnames, init_fcn, *args):
        self.world_vars = world_varnames
        self.agent_vars = agent_varnames
        self.initializer = lambda x,y: init_fcn(x, y, *args)

    def addWorldChannel(self, channel, name=None, wc_dependents=[], ac_dependents=[]):
        """
        Add a world channel instance to the model.

        """
        if name is None:
            name = channel._id
        else:
            channel._id = name

        if name in self.world_channel_table:
            raise ValueError("A channel with the same name has already been included in the model.")
        elif not isinstance(channel, WorldChannel):
            raise TypeError("A world channel instance is required.")
        self.world_channel_table[name] = _ChannelEntry(channel, wc_dependents, ac_dependents, False)

    def addAgentChannel(self, channel, name=None, wc_dependents=[], ac_dependents=[], sync=False):
        """
        Add an agent channel instance to the model.

        """
        if name is None:
            name = channel._id
        else:
            channel._id = name
            
        if name in self.agent_channel_table:
            raise ValueError("A channel with the same name has already been included in the model.")
        elif not isinstance(channel, AgentChannel):
            raise TypeError("An agent channel instance is required.")
        self.agent_channel_table[name] = _ChannelEntry(channel, wc_dependents, ac_dependents, sync)

    def addLogger(self, agent_index, logged_varnames, logging_fcn=None):
        if not 0 <= agent_index < self.nmax:
            raise ValueError("Lineage to be tracked must be specified as an index between 0 and init_num_agents.")
        self.logged[agent_index] = (logged_varnames, logging_fcn)

    def addRecorder(self, recorder):
        self.recorders.append(recorder)





#-------------------------------------------------------------------------------
# Factory functions for creating entities from model input data

def create_agents(model, simulator, t_init):
    """
    Factory for agent entities.

    """
    agents = []
    from cps.logging import LoggerNode
    from cps.entity import Scheduler
    for i in range(model.n0):
        # create channel network/event schedule
        state_names = model.agent_vars
        scheduler = Scheduler.agentSchedulerFromModel(t_init, model.agent_channel_table, model.world_channel_table)
        # create agent
        if i in model.logged:
            # make logger here
            names, loggingfcn = model.logged[i]
            agents.append( model.LoggedAgentType(state_names, scheduler, simulator, LoggerNode(names, loggingfcn)) )
        else:
            agents.append( model.AgentType(state_names, scheduler, simulator) )
    return agents

def create_world(model, simulator, t_init):
    """
    Factory for world entities.

    """
    from cps.entity import Scheduler
    # create channel scheduler
    state_names = model.world_vars
    scheduler = Scheduler.worldSchedulerFromModel(t_init, model.world_channel_table)
    # create world
    return model.WorldType(state_names, scheduler, simulator)





















# example...
def main():
    def init(cells, gdata, data):
        # initialize simulation entities
        pass

    def my_logger(state):
        # decide what to record...make sure reference types are copied
        return [state.x[:], state.y[0]]

    w1 = WorldChannel()
    w2 = WorldChannel()
    a1 = AgentChannel()
    a2 = AgentChannel()
    a3 = AgentChannel()

    model = Model(init_num_agents=2,
                  max_num_agents=100,
                  world_vars=['A', 'B', 'C'],
                  agent_vars=['x', 'y', 'z'],
                  initializer=init,
                  logger=my_logger)

    model.addWorldChannel('W1', w1, [], [w2])
    model.addWorldChannel(name='W2',
                          channel=w2,
                          ac_dependents=[a1],
                          wc_dependents=[])
    model.addAgentChannel(name='A1',
                          channel=a1,
                          ac_dependents=[],
                          wc_dependents=[w1],
                          sync=True)
    model.addAgentChannel(name='A2',
                          channel=a2,
                          ac_dependents=[a1,a3],
                          wc_dependents=[])
    model.addAgentChannel(name='A3',
                          channel=a3,
                          ac_dependents=[],
                          wc_dependents=[])

    print()

if __name__ == '__main__':
    main()
