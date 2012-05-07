"""
Name:        simulator

Author:      Nezar Abdennur <nabdennur@gmail.com>

Created:     23/04/2012
Copyright:   (c) Nezar Abdennur 2012

"""
#!/usr/bin/env python

from cps.entity import World, Agent, LineageAgent, AgentQueue, create_agent, create_world
from cps.misc import IndexedPriorityQueue
import random

class BaseSimulator(object):
    """
    Base class for simulation managers.

    """
    def __init__(self, model, tstart):
        """
        Create world and agent entities according to model.
        Attributes:
            num_agents (int)
            max_num_agents (int)
            world (World)
            agents (list-of-Agent)
            root_nodes (list-of-DataLogNode)

        """
        # keep count of agents
        self.num_agents = model.init_num_agents
        self.max_num_agents = model.max_num_agents

        # create world entity
        self.world = create_world(tstart,
                                  model.world_channel_table,
                                  model.world_vars)

        # create agent entities
        self.agents = []
        self.root_nodes = []
        for i in range(self.num_agents):
            if i in model.track_lineage:
                agent = create_agent(LineageAgent,
                                     tstart,
                                     model.agent_channel_table,
                                     model.world_channel_table,
                                     model.agent_vars,
                                     model.logger)
                self.agents.append(agent)
                self.root_nodes.append(agent.node)
            else:
                self.agents.append(create_agent(Agent,
                                                tstart,
                                                model.agent_channel_table,
                                                model.world_channel_table,
                                                model.agent_vars,
                                                model.logger))

        # initialization routine
        self._initializer = lambda x,y: model.initializer(x,y,model.parameters)

        # create queues
        self._agent_queue = AgentQueue()

    def initialize(self):
        raise NotImplementedError

    def runSimulation(self, tstop):
        raise NotImplementedError



#-------------------------------------------------------------------------------
# First-Entity (synchronous) Method

class FEMethodSimulator(BaseSimulator):
    def __init__(self, model, tstart):
        """
        Additional attributes:
            timetable (IndexedPriorityQueue)

        """
        super(FEMethodSimulator, self).__init__(model, tstart)
        self.timetable = None

    def initialize(self):
        """
        Apply user-defined initialization function and schedule all simulation
        channels.

        """
        # initialize state variables with user-defined function
        self._initializer(self.agents, self.world)
        # schedule simulation channels
        self.world.scheduleAllChannels(self.agents)
        for agent in self.agents:
            agent.scheduleAllChannels(self.world)

        # set up global timetable
        event_times = [self.world.next_event_time]
        entities = [self.world]
        for agent in self.agents:
            event_times.append(agent.next_event_time)
            entities.append(agent)
        self.timetable = IndexedPriorityQueue(entities, event_times)

    def runSimulation(self, tstop):
        """
        Perform a simulation from initial simulation clock time until tstop.
        The algorithm is called the First-Entity Method.

        """
        q = self._agent_queue
        agents = self.agents
        world = self.world

        # get earliest event time and entity
        tmin, emin = self.timetable.peekMin()

        while (tmin <= tstop):
            if emin is world:
                # synchronize agents with the world (fire gap channels)
                for agent in agents:
                    agent.synchronize(tmin, world, q)
                    self.timetable.update(agent, agent.next_event_time)

                # next world event
                world.fireNextChannel(agents, q)
                world.rescheduleDependentChannels(agents)
                ##world.closeGaps(tmin, agents, aq, rq)
                self.timetable.update(world, world.next_event_time)
                if not world.is_enabled: # terminate simulation prematurely
                    return

                # reschedule agent channels affected by world event
                if world.is_modified:
                    for agent in agents:
                        agent.rescheduleG2L(world, world)
                        self.timetable.update(agent, agent.next_event_time)

            elif emin.is_enabled:      #(emin is an agent)
                # next agent event
                emin.fireNextChannel(world, q)
                emin.rescheduleDependentChannels(world)
                self.timetable.update(emin, emin.next_event_time)

                # reschedule world channels affected by agent event
                if emin.is_modified:
                    world.rescheduleL2G(agents, emin)
                    self.timetable.update(world, world.next_event_time)

             # add/substitute new agents
            self._processAgentQueue(tmin)

            # get earliest event and entity
            tmin, emin = self.timetable.peekMin()
        #endwhile

    def _processAgentQueue(self, tbarrier):
        while self._agent_queue:
            action, new_agent = self._agent_queue.dequeue()

            if action == AgentQueue.ADD_AGENT:
                parent = new_agent._parent

                # Finalize the event which added this agent to the queue
                # Update agent's schedule
                new_agent.finalizePrevEvent()
                new_agent.reschedulePrevChannel(self.world)
                new_agent.rescheduleDependentChannels(self.world)
                #NOTE: no need to fire sync channels here

                if self.num_agents < self.max_num_agents:
                    # NORMAL MODE: Add agent to population
                    # add to agent list
                    self.agents.append(new_agent)
                    # add to ipq
                    self.timetable.add(new_agent, new_agent.next_event_time)
                    self.num_agents += 1
                else:
                    # CONSTANT-NUMBER MODE: Substitute agent into population
                    index = random.randint(0, len(self.agents)-1)
                    target = self.agents[index]
                    # substitute in agent list
                    self.agents[index] = new_agent
                    # substitute in ipq
                    self.timetable.replace(target, new_agent, new_agent.next_event_time)
                    del target

            elif action == AgentQueue.DELETE_AGENT:
                target = item

                if self.num_agents < self.max_num_agents:
                    # NORMAL MODE: Remove agent from population
                    try:
                        self.agents.remove(target)
                    except ValueError:
                        raise SimulationError("Agent not found.")

                    self.timetable.remove(target) #TODO: implement this!!!
                    self.num_agents -= 1

                    if self.num_agents == 0:
                        raise SimulationError("The population crashed!")

                else:
                    # CONSTANT-NUMBER MODE: Substitute with a randomly chosen
                    # agent
                    try:
                        i_target = self.agents.index(target)
                    except ValueError:
                        raise SimulationError("Agent not found.")

                    # pick random agent to copy
                    i_source = i_target
                    while i_source == i_target:
                        i_source = random.randint(0, self.num_agents-1)

                    # replace target agent
                    new_agent = self.agents[i_source].clone()
                    self.agents[i_target] = new_agent
                    self.timetable.replace(target, new_agent, new_agent.next_event_time)
                    del target




#-------------------------------------------------------------------------------
# Asynchronous Method

class AsyncMethodSimulator(BaseSimulator):
    def initialize(self):
        """
        Apply user-defined initialization function and schedule all simulation
        channels.

        """
        self._initializer(self.agents, self.world)
        self.world.scheduleAllChannels(self.agents)
        for agent in self.agents:
            agent.scheduleAllChannels(self.world)

    def runSimulation(self, tstop):
        """
        Perform a simulation from initial simulation clock time until tstop.
        The algorithm is called the Asynchronous Method.

        """
        q = self._agent_queue
        agents = self.agents
        world = self.world

        tsync = world.next_event_time

        while (tsync <= tstop):
            # release agents to sync time barrier
            pending_world_channels = set()
            for agent in agents:
                    clock = agent.next_event_time
                    while agent.is_enabled and clock <= tsync:
                        agent.fireNextChannel(world, q)

                        # collect affected world channels
                        # ***NOTE: Allowing this could be problematic...
                        wcs = agent.getDependentWorldChannels()
                        if wcs and world.is_modified:
                            for wc in wcs:
                                pending_world_channels.add(wc)

                        agent.rescheduleDependentChannels(world)
                        clock = agent.next_event_time
                    agent.synchronize(tsync, world, q)

            # add/substitute new agents
            self._processAgentQueue(tsync)

            # reschedule world channels affected by agent events
            # ***NOTE: Allowing this could be problematic...
            world.rescheduleL2GAsync(agents, pending_world_channels)

            # next world event
            world.fireNextChannel(agents, q)
            world.rescheduleDependentChannels(agents)
            ##world.closeGaps(tsync, agents, aq, rq)

            # reschedule agent events affected by world event
            if world.is_modified:
                for agent in agents:
                    agent.rescheduleG2L(world, world)

            # next sync barrier
            tsync = world.next_event_time

    def _processAgentQueue(self, tsync):

        replaced = set()

        while self._agent_queue:
            action, new_agent = self._agent_queue.dequeue()

            if action == AgentQueue.ADD_AGENT:
                parent = new_agent._parent

                if self.num_agents < self.max_num_agents:
                    # NORMAL MODE: Add agent to population

                    # Update child agent's event schedule
                    new_agent.finalizePrevEvent()
                    new_agent.reschedulePrevChannel(self.world)
                    new_agent.rescheduleDependentChannels(self.world)
                    #new_agent.synchronize(tsync, self.world, self._agent_queue)

                    # Add agent
                    self.agents.append(new_agent)
                    self.num_agents += 1

                elif parent not in replaced:
                    # CONSTANT-NUMBER MODE: Substitute new agent into population

                    # Update child agent's event schedule to mirror parent's
                    new_agent.finalizePrevEvent()
                    new_agent.reschedulePrevChannel(self.world)
                    new_agent.rescheduleDependentChannels(self.world)
                    #new_agent.synchronize(tsync, self.world, self._agent_queue)

                    # Replace a randomly chosen agent
                    index = random.randint(0, len(self.agents)-1)
                    replaced.add(self.agents[index])
                    self.agents[index] = new_agent

                else:
                    # This agent's parent has been replaced by another agent
                    # --> discard this agent
                    del new_agent

            elif action == AgentQueue.DELETE_AGENT:
                target = item

                if self.num_agents < self.max_num_agents:
                    # NORMAL MODE: Remove agent from population

                    try:
                        self.agents.remove(target)
                    except ValueError:
                        raise SimulationError("Agent not found.")
                    self.num_agents -= 1

                    if self.num_agents == 0:
                        raise SimulationError("The population crashed!")

                elif target not in replaced:
                    # CONSTANT-NUMBER MODE: Replace deleted agent with a copy
                    # of a randomly selected agent

                    try:
                        i_target = self.agents.index(target)
                    except ValueError:
                        raise SimulationError("Agent not found.")

                    # pick random agent to copy
                    i_source = i_target
                    while i_source == i_target:
                        i_source = random.randint(0, self.num_agents-1)

                    # replace target agent
                    self.agents[i_target] = self.agents[i_source].clone()
                    del target

                else:
                    # This agent has already been replaced --> discard
                    del target

        replaced.clear()
        del replaced



def main():
    pass

if __name__ == '__main__':
    main()
