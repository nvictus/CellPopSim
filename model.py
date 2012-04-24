#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      Nezar
#
# Created:     23/04/2012
# Copyright:   (c) Nezar 2012
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python

class Model(object):
    """
    Specify an agent-based model.
    The Model constructor requires the following:
        init_num_agents (int): the initial number of agents to create
        max_num_agents (int): the maximum number of agents allowed
        init_fcn (function): an user-defined function to initialize the states
                             of the entities
        parameters (any): user data to pass to the initialization function
        world_vars (list-of-string): names of global state variables
        agent_vars (list-of-string): names of local state variables

    The last thing to be added is simulation channels. These require information
    including a qualified name and global and local dependencies.
        addWorldChannel() to add a world channel
        addAgentChannel() to add an agent channel

    """
    # Store simulation channel information in a table of entries according to
    class ChannelEntry(object):
        def __init__(self, channel, name, is_gap, wc_dependents=None, ac_dependents=None):
            channel.id = name
            self.name = name
            self.channel = channel
            self.is_gap = is_gap
            self.ac_dependents = ac_dependents if ac_dependents is not None else []
            self.wc_dependents = wc_dependents if wc_dependents is not None else []

    def __init__(self, init_num_agents,
                       max_num_agents,
                       world_vars,
                       agent_vars,
                       init_fcn,
                       parameters,
                       logger=None,
                       track_lineage=[]):
        self.init_num_agents = init_num_agents
        self.max_num_agents = max_num_agents
        self.init_fcn = init_fcn
        self.parameters = parameters
        self.world_vars = world_vars
        self.agent_vars = agent_vars
        self.logger = logger
        self.track_lineage = track_lineage
        self.world_channel_table = []
        self.agent_channel_table = []

    def addWorldChannel(self, **kwargs):
        self.world_channel_table.append(Model.ChannelEntry(**kwargs))

    def addAgentChannel(self, **kwargs):
        self.agent_channel_table.append(Model.ChannelEntry(**kwargs))

def main():
    pass

if __name__ == '__main__':
    main()
