#-------------------------------------------------------------------------------
# Name:        module1
# Purpose:
#
# Author:      Nezar
#
# Created:     11/01/2012
# Copyright:   (c) Nezar 2012
# Licence:     <your licence>
#-------------------------------------------------------------------------------
#!/usr/bin/env python

from base import *
from misc import *
import random


class Model(object):
    """
    Specify an agent-based model.

    """
    class ChannelEntry(object):
        def __init__(self, channel, name, is_gap, wc_dependents=None, ac_dependents=None):
            self.name = name
            self.channel = channel
            self.is_gap = is_gap
            self.ac_dependents = ac_dependents if ac_dependents is not None else []
            self.wc_dependents = wc_dependents if wc_dependents is not None else []

    def __init__(self, init_num_agents, max_num_agents, world_vars, agent_vars, init_fcn, parameters):
        self.init_num_agents = init_num_agents
        self.max_num_agents = max_num_agents
        self.init_fcn = init_fcn
        self.parameters = parameters
        self.world_vars = world_vars
        self.agent_vars = agent_vars
        self.world_channel_table = []
        self.agent_channel_table = []

    def addWorldChannel(self, **kwargs):
        self.world_channel_table.append(Model.ChannelEntry(**kwargs))

    def addAgentChannel(self, **kwargs):
        self.agent_channel_table.append(Model.ChannelEntry(**kwargs))


class AbstractManager(object):
    """
    Base class for simulation managers.

    """
    def __init__(self, model, tstart):
        # agent counter
        self.num_agents = model.init_num_agents
        self.max_num_agents = model.max_num_agents

        # create entities
        self.world = self._createWorld(tstart,
                                       model.world_vars,
                                       model.world_channel_table)
        self.agents = self._createAgents(model.init_num_agents,
                                         tstart,
                                         model.agent_vars,
                                         model.agent_channel_table,
                                         model.world_channel_table)

        # create queues
        self._add_queue = AgentQueue()
        self._rem_queue = AgentQueue()

    def initialize(self):
        raise(NotImplementedError)

    def runSimulation(self, tstop):
        raise(NotImplementedError)

    def _createWorld(self, t_init, var_names, wc_table):
        channel_index = {}
        dep_graph = {}
        gap_channels = []
        for entry in wc_table:
            channel_index[entry.name] = copy(entry.channel)
            dep_graph[entry.channel] = tuple([copy(channel) for channel in entry.wc_dependents])
            if entry.is_gap:
                gap_channels.append(entry.channel)
        state = State(var_names)
        engine = EngineImpl(t_init, channel_index, gap_channels, dep_graph)
        return World(t_init, state, engine)

    def _createAgents(self, num_agents, t_init, var_names, ac_table, wc_table):
        agents = []
        for i in range(num_agents):
            channel_index = {}
            dep_graph = {}
            l2g_graph = {}
            g2l_graph = {}
            gap_channels = []
            map_copied = {entry.channel:copy(entry.channel) for entry in ac_table}
            for entry in ac_table:
                channel_index[entry.name] = map_copied[entry.channel]
                dep_graph[map_copied[entry.channel]] = tuple([map_copied[channel] for channel in entry.ac_dependents])
                l2g_graph[map_copied[entry.channel]] = entry.wc_dependents
                if entry.is_gap:
                    gap_channels.append(map_copied[entry.channel])
            for entry in wc_table:
                g2l_graph[entry.channel] = tuple([copy(channel) for channel in entry.ac_dependents])

            state = State(var_names)
            engine = EngineImpl(t_init, channel_index, gap_channels, dep_graph, l2g_graph, g2l_graph)
            agents.append(Agent(t_init, state, engine))
        return agents


class FEMethodManager(AbstractManager):
    def __init__(self, model, tstart):
        """
        Attributes:
            num_agents (int)
            max_num_agents (int)
            agents (Agent)
            world (World)
            add_queue (AgentQueue)
            rem_queue (AgentQueue)
            timetable (IndexedPriorityQueue)

        """
        super(FEMethodManager, self).__init__(model, tstart)

        # initialize entities
        self.initialize(model)

        # set up global timetable
        event_times = [self.world.getNextEventTime()]
        entities = [self.world]
        for agent in self.agents:
            event_times.append(agent.getNextEventTime())
            entities.append(agent)
        self.timetable = IndexedPriorityQueue(entities, event_times)

    def initialize(self, model):
        # initialize state variables with user-defined function
        model.init_fcn(self.agents, self.world, model.parameters)
        # schedule simulation channels
        self.world.scheduleAllChannels(self.agents)
        for agent in self.agents:
            agent.scheduleAllChannels(self.world)

    def runSimulation(self, tstop):
        aq = self._add_queue
        rq = self._rem_queue
        agents = self.agents
        world = self.world

        # get earliest event time and entity
        tmin, emin = self.timetable.peekMin()

        while (tmin <= tstop):
            if emin is world:
                # synchronize agents with the world (fire gap channels)
                for agent in agents:
                    agent.closeGaps(tmin, world, aq, rq) #!!!!!!
                    self.timetable.update(agent, agent.getNextEventTime())

                # next world event
                world.fireNextChannel(agents, aq, rq) #!!!!!!
                world.rescheduleDependentChannels(agents) #!!!!!
                world.closeGaps(tmin, agents, aq, rq) #!!!!!!
                self.timetable.update(world, world.getNextEventTime())
                if not world._enabled: # terminate simulation prematurely
                    return

                # reschedule agent channels affected by world event
                if world.is_modified:
                    for agent in agents:
                        agent.rescheduleAux(world, world) #!!!!!!
                        self.timetable.update(agent, agent.getNextEventTime())

            elif emin._enabled:      #(emin is an agent)
                # next agent event
                emin.fireNextChannel(world, aq, rq) #!!!!!!
                emin.rescheduleDependentChannels(world) #!!!!!!
                self.timetable.update(emin, emin.getNextEventTime())

                # reschedule world channels affected by agent event
                if emin.is_modified:
                    world.rescheduleAux(agents, emin) #!!!!!!
                    self.timetable.update(world, world.getNextEventTime())

             # add/substitute new agents
            self._processAgentQueues(tmin)

            # get earliest event and entity
            tmin, emin = self.timetable.peekMin()
        #endwhile

    def _processAgentQueues(self, tbarrier):
        while not self._add_queue.isEmpty():
            parent, new_agent = self._add_queue.popAgent()

            # Update child agent's engine to mirror parent's
            new_agent.clock = parent.clock
            new_agent.is_modified = parent.is_modified
            new_agent.rescheduleLastChannel(self.world) #!!!!!!
            new_agent.rescheduleDependentChannels(self.world) #!!!!!!
            #no need to fire gap channels!

            # Add or substitute new agent
            if self.num_agents < self.max_num_agents:
                # add to manager
                self.agents.append(new_agent)
                # add to ipq
                self.timetable.add(new_agent, new_agent.getNextEventTime())
                self.num_agents += 1
            else:
                index = random.randint(0, len(self.agents)-1)
                target_agent = self.agents[index]
                # substitute in manager
                self.agents[index] = new_agent
                # substitute in ipq
                self.timetable.replace(target_agent, new_agent, new_agent.getNextEventTime())
                del target_agent


class AsyncMethodManager(AbstractManager):
    def __init__(self, model, tstart):
        """
        Attributes:
            num_agents (int)
            max_num_agents (int)
            agents (Agent)
            world (World)
            add_queue (AgentQueue)
            rem_queue (AgentQueue)

        """
        super(AsyncMethodManager, self).__init__(model, tstart)
        self.initialize(model)

    def initialize(self, model):
        model.init_fcn(self.agents, self.world, model.parameters)
        self.world.scheduleAllChannels(self.agents)
        for agent in self.agents:
            agent.scheduleAllChannels(self.world)

    def runSimulation(self, tstop):
        aq = self._add_queue
        rq = self._rem_queue
        agents = self.agents
        world = self.world

        tsync = world.getNextEventTime()

        while (tsync <= tstop):
            # release agents to sync time barrier
            pending_world_channels = set()
            for agent in agents:
                if agent._enabled:
                    clock = agent.getNextEventTime()
                    while clock <= tsync:
                        agent.fireNextChannel(world, aq, rq) #!!!!!!

                        # collect affected world channels
                        wcs = agent.getDependentWorldChannels()
                        if wcs and world.is_modified:
                            for wc in wcs:
                                pending_world_channels.add(wc)

                        agent.rescheduleDependentChannels(world) #!!!!!!
                        clock = agent.getNextEventTime()
                    agent.closeGaps(tsync, world, aq, rq) #!!!!!!

            # add/substitute new agents
            self._processAgentQueues(tsync)

            # reschedule world channels affected by agent events
            world.rescheduleAuxAsync(agents, pending_world_channels)

            # next world event
            world.fireNextChannel(agents, aq, rq) #!!!!!!
            world.rescheduleDependentChannels(agents) #!!!!!!
            world.closeGaps(tsync, agents, aq, rq) #!!!!!!

            # reschedule agent events affected by world event
            if world.is_modified:
                for agent in agents:
                    agent.rescheduleAux(world, world) #!!!!!!

            # next sync barrier
            tsync = world.getNextEventTime()

    def _processAgentQueues(self, tsync):
        targets = set()
        while not self._add_queue.isEmpty():
            parent, new_agent = self._add_queue.popAgent()

            # Update child agent's engine to mirror parent's
            new_agent.clock = parent.clock
            new_agent.is_modified = parent.is_modified
            new_agent.rescheduleLastChannel(self.world) #!!!!!!
            new_agent.rescheduleDependentChannels(self.world) #!!!!!!
            new_agent.closeGaps(tsync, self.world, self._add_queue, self._rem_queue) #!!!!!!

            # Add or substitute new agent
            if self.num_agents < self.max_num_agents:
                #add agent
                self.agents.append(new_agent)
                self.num_agents += 1
            elif parent not in targets:
                #replace a randomly chosen agent
                index = random.randint(0, len(self.agents)-1)
                targets.add(self.agents[index])
                self.agents[index] = new_agent
            else:      #(this agent's parent has been replaced by another agent)
                del new_agent #discard this agent

        if targets:
            for target in targets:
                del target
            del targets




#-------------------------------------------------------------------------------
def main():
    pass

if __name__ == '__main__':
    main()