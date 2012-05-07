"""
Name:        model

Author:      Nezar Abdennur <nabdennur@gmail.com>
Created:     23/04/2012
Copyright:   (c) Nezar Abdennur 2012

"""
#!/usr/bin/env python

from cps.channel import AgentChannel, WorldChannel
import collections

# Store simulation channel information in a table of entries specified by
_ChannelEntry = collections.namedtuple('ChannelEntry', 'channel wc_dependents ac_dependents sync')

class Model(object):
    """
    Specify an agent-based model.

    The Model constructor requires the following:
        init_num_agents (int): the initial number of agents to create

        max_num_agents (int): the maximum number of agents allowed

        initializer (callable): a user-defined function to initialize the states
                                of the world and agents

        world_vars (list-of-string): names of world state variables

        agent_vars (list-of-string): names of agent state variables


    The following are optional:
        parameters (any): user data to pass to the initializer [default=None]

        track_lineage (list-of-int): indices referring to initial agents whose
                                     state history will be logged along with
                                     those of their descendants [default=no tracking]
        logger (callable): user-defined function that returns data to be logged
                           for lineage tracking -- [the default logger records
                           all agent state variables]


    The last thing to be added are the simulation channels. These require
    information including a qualified name and global and local dependencies.
    Use the following methods to add channels:
        addWorldChannel() to add a world channel

        addAgentChannel() to add an agent channel

    """
    def __init__(self, init_num_agents,
                       max_num_agents,
                       world_vars,
                       agent_vars,
                       initializer,
                       parameters=None,
                       track_lineage=[],
                       logger=None):

        self.world_channel_table = {}
        self.agent_channel_table = {}

        # Required arguments
        if init_num_agents > max_num_agents:
            raise ValueError("Must have initial # agents <= maximum # agents.")
        self.init_num_agents = init_num_agents
        self.max_num_agents = max_num_agents
        self.world_vars = world_vars
        self.agent_vars = agent_vars
        self.initializer = initializer

        # Optional arguments
        if logger is not None and not callable(logger):
            raise TypeError("Logger must be callable and take 1 argument.")
        if track_lineage and any ([not 0 <= i < init_num_agents for i in track_lineage]):
            raise ValueError("Lineages to be tracked must be specified as a list of integers between 0 and init_num_agents.")
        self.parameters = parameters
        self.logger = logger
        self.track_lineage = track_lineage

    def addWorldChannel(self, channel, name=None, wc_dependents=[], ac_dependents=[]):
        """
        Add a world channel instance to the model.

        """
        if name is None:
            name = channel.__class__
        if name in self.world_channel_table:
            raise ValueError("A channel with the same name has already been included in the model.")
        elif not isinstance(channel, WorldChannel):
            raise TypeError("A world channel instance is required.")

        channel.id = name
        self.world_channel_table[name] = _ChannelEntry(channel, wc_dependents, ac_dependents, False)

    def addAgentChannel(self, channel, name=None, wc_dependents=[], ac_dependents=[], sync=False):
        """
        Add an agent channel instance to the model.

        """
        if name is None:
            name = channel.__class__
        if name in self.agent_channel_table:
            raise ValueError("A channel with the same name has already been included in the model.")
        elif not isinstance(channel, AgentChannel):
            raise TypeError("An agent channel instance is required.")

        channel.id = name
        self.agent_channel_table[name] = _ChannelEntry(channel, wc_dependents, ac_dependents, sync)



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
                  logger=my_logger,
                  track_lineage=[0])

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
