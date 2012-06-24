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
        n0   (int): the initial number of agents to create
        nmax (int): the maximum number of agents allowed

    A functional model also needs:
    1. An initializer:
        addInitializer() to add a state initializer

    2. Simulation Channels:
        addWorldChannel() to add a world channel
        addAgentChannel() to add an agent channel

    Optional:
    3. Loggers:
        addLogger() to attach a logger to an agent to monitor it and its descendants

    4. Recorders:
        addRecorder() to add a recorder to the simulator

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
        self.logged = {}
        self.recorders = []
        self.world_channel_table = {}
        self.agent_channel_table = {}

    def addInitializer(self, world_varnames, agent_varnames, init_fcn, *args):
        """
        Add a function to initialize the states of the world and agent entities.
        The simulator will use this before a simulation run begins.

        Arguments:
            world_vars (list-of-string): names of world state variables
            agent_vars (list-of-string): names of agent state variables
            init_fcn   (callable): a user-defined function with signature f(world, agents, ...)
        Optional:
            *args: extra arguments to be passed to the init_fcn

        """
        self.world_vars = world_varnames
        self.agent_vars = agent_varnames
        self.initializer = lambda x,y: init_fcn(x, y, *args)

    def addWorldChannel(self, channel, name=None, wc_dependents=[], ac_dependents=[]):
        """
        Add a world channel instance to the model.

        Arguments:
            channel (cps.channel.WorldChannel)
        Optional:
            name (default=class's name): a unique key to identify a channel from the other world channels
            wc_dependents (default=[]): a list of world channel instances that depend on this world channel
            ac_dependents (default=[]): a list of agent channel instances that depend on this world channel

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
        Each agent will receive a copy of the instance provided.

        Arguments:
            channel (cps.channel.AgentChannel)
        Optional:
            name (default=class's name): a unique key to identify a channel from the other agent channels
            wc_dependents (default=[]): a list of world channel instances that depend on this agent channel
            ac_dependents (default=[]): a list of agent channel instances that depend on this agent channel

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
        """
        Monitor the event history of an agent and its offspring by attaching a logger to it.
        The logging function is called after each channel firing to record custom information about
        the agent's state.

        Arguments:
            agent_index (int): index between 0 and n0-1 specifying which initial agent to track
            logged_varnames (list-of-string): names of quantities being logged
            logging_fcn (callable): a user-defined function with signature f(log, event_time, agent)

        """
        if not 0 <= agent_index < self.nmax:
            raise ValueError("Agent lineage to be tracked must be specified as an index between 0 and n0.")
        self.logged[agent_index] = (logged_varnames, logging_fcn)

    def addRecorder(self, recorder):
        """
        Record global information about the population state.
        The simulator records information at the initial and final times of a simulation run.
        World channels with a reference to the same recorder can be used to record the population
        state at intervening times.

        Arguments:
            recorder (cps.channel.Recorder): recorder object that possesses a record method
            The recording function has signature f(log, event_time, world, agents)

        """
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


