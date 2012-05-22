"""
Name:        simulator

Author:      Nezar Abdennur <nabdennur@gmail.com>

Created:     23/04/2012
Copyright:   (c) Nezar Abdennur 2012

"""
#!/usr/bin/env python

from cps.entity import World, Agent, LineageAgent, AgentQueue, create_agent, create_world
from cps.misc import IndexedPriorityQueue
from cps.exception import SimulationError, ZeroPopulationError
import random

NORMAL = 0
CONSTANT_NUMBER = 1

class BaseSimulator(object):
    """
    Base class for simulators.

    Attributes:
        num_agents       (int)
        max_num_agents   (int)
        theoretical_size (float)
        world            (cps.entity.World)
        agents           (list-of-cps.entity.Agent)
        root_nodes       (list-of-cps.state.DataLogNode)

    """
    def __init__(self, model, tstart):
        """
        Initialize a simulator according to the specification of the provided
        model.

        """
        # keep count of agents
        self.num_agents = model.init_num_agents
        self.max_num_agents = model.max_num_agents
        self.theoretical_size = self.num_agents

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

        self.initialize()

    def initialize(self):
        raise NotImplementedError

    def runSimulation(self, tstop):
        raise NotImplementedError



#-------------------------------------------------------------------------------
# First-Entity (synchronous) Method

class FEMethodSimulator(BaseSimulator):
    """
    Additional attributes:
        timetable (IndexedPriorityQueue)

    """
    def initialize(self):
        if self.num_agents < self.max_num_agents:
            self._mode = NORMAL
        else:
            self._mode = CONSTANT_NUMBER

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
        self.timetable = IndexedPriorityQueue(zip(entities, event_times))

    def runSimulation(self, tstop):
        """
        Perform a simulation from initial simulation clock time until tstop.
        The algorithm is called the First-Entity Method.

        """
        q = self._agent_queue
        agents = self.agents
        world = self.world

        # get earliest event time and entity
        emin, tmin = self.timetable.peek()

        while (tmin <= tstop):
            if emin is world:
                # synchronize agents with the world (fire sync channels)
                for agent in agents:
                    agent.synchronize(tmin, world, q)
                    self.timetable.updateitem(agent, agent.next_event_time)

                # next world event
                world.fireNextChannel(agents, q)
                world.rescheduleDependentChannels(agents)
                self.timetable.updateitem(world, world.next_event_time)
                if not world.is_enabled: # terminate simulation prematurely
                    return

                # reschedule agent channels affected by world event
                if world.is_modified:
                    for agent in agents:
                        agent.crossScheduleG2L(world, world)
                        self.timetable.updateitem(agent, agent.next_event_time)

            elif emin.is_enabled:      #(emin is an agent)
                # next agent event
                emin.fireNextChannel(world, q)
                emin.rescheduleDependentChannels(world)
                self.timetable.updateitem(emin, emin.next_event_time)

                # reschedule world channels affected by agent event
                if emin.is_modified:
                    world.crossScheduleL2G(agents, emin)
                    self.timetable.updateitem(world, world.next_event_time)

             # add/substitute new agents
            while q:
                action, agent = q.dequeue()
                if self._mode == NORMAL:
                    self._processAgentNormalMode(action, agent)
                else:
                    self._processAgentConstantNumberMode(action, agent)
            world.size = self.theoretical_size

            # get earliest event and entity
            emin, tmin = self.timetable.peek()
        #endwhile

    def _processAgentNormalMode(self, action, agent):
        if action == AgentQueue.ADD_AGENT:
            new_agent = agent
            parent = new_agent._parent

            # Finalize the event which added this agent to the queue
            # and update agent's schedule
            new_agent.finalizePrevEvent() #removes _parent reference
            new_agent.reschedulePrevChannel(self.world)
            new_agent.rescheduleDependentChannels(self.world)

            self.agents.append(new_agent)
            self.timetable.add(new_agent, new_agent.next_event_time)
            self.num_agents += 1
            self.theoretical_size += 1

            # Switch modes if we reach the size threshold
            if self.num_agents == self.max_num_agents:
                self._mode = CONSTANT_NUMBER

        elif action == AgentQueue.DELETE_AGENT:
            target = agent
            # Remove agent from population
            try:
                self.agents.remove(target)
            except ValueError:
                raise SimulationError("Agent not found.")

            self.timetable.pop(target)
            self.num_agents -= 1
            self.theoretical_size -= 1

            if self.num_agents == 0:
                raise ZeroPopulationError("The population crashed!")

    def _processAgentConstantNumberMode(self, action, agent):
        if action == AgentQueue.ADD_AGENT:
            new_agent = agent
            parent = new_agent._parent

            # Finalize the event which added this agent to the queue
            # and update agent's schedule
            new_agent.finalizePrevEvent() #removes _parent reference
            new_agent.reschedulePrevChannel(self.world)
            new_agent.rescheduleDependentChannels(self.world)

            # Replace a randomly chosen agent
            index = random.randint(0, len(self.agents)-1)
            target = self.agents[index]
            # substitute in agent list and ipq
            self.agents[index] = new_agent
            self.timetable.replaceitem(target, new_agent, new_agent.next_event_time)
            del target
            self.theoretical_size += self.theoretical_size/self.num_agents

        elif action == AgentQueue.DELETE_AGENT:
            if self.num_agents <= 1:
                raise SimulationError

            target = agent
            try:
                i_target = self.agents.index(target)
            except ValueError:
                raise SimulationError("Agent not found.")

            # Replace with a randomly chosen agent
            # pick random agent to copy
            i_source = i_target
            while i_source == i_target:
                i_source = random.randint(0, self.num_agents-1)

            # replace target agent
            new_agent = self.agents[i_source].clone(); new_agent._parent = None
            self.agents[i_target] = new_agent
            self.timetable.replaceitem(target, new_agent, new_agent.next_event_time)
            del target
            self.theoretical_size -= self.theoretical_size/self.num_agents

            # Switch to normal mode if the theoretical size drops below
            # the constant-number threshold
##                    if self.theoretical_size < self.max_num





##    def _processAgentQueue(self, tbarrier):
##        while self._agent_queue:
##            action, agent = self._agent_queue.dequeue()
##
##            if action == AgentQueue.ADD_AGENT:
##                new_agent = agent
##                parent = new_agent._parent
##
##                # Finalize the event which added this agent to the queue
##                # and update agent's schedule
##                new_agent.finalizePrevEvent() #removes _parent reference
##                new_agent.reschedulePrevChannel(self.world)
##                new_agent.rescheduleDependentChannels(self.world)
##
##                if self._mode == NORMAL:   #self.num_agents < self.max_num_agents
##                    # Add to agent to population (list and ipq)
##                    self.agents.append(new_agent)
##                    self.timetable.add(new_agent, new_agent.next_event_time)
##                    self.num_agents += 1
##                    self.theoretical_size += 1
##
##                    # Switch modes if we reach the size threshold
##                    if self.num_agents == self.max_num_agents:
##                        self._mode = CONSTANT_NUMBER
##
##                else: #_mode == CONSTANT_NUMBER
##                    # Substitute agent into population
##                    index = random.randint(0, len(self.agents)-1)
##                    target = self.agents[index]
##                    # substitute in agent list and ipq
##                    self.agents[index] = new_agent
##                    self.timetable.replaceitem(target, new_agent, new_agent.next_event_time)
##                    del target
##                    self.theoretical_size += self.theoretical_size/self.num_agents
##
##            elif action == AgentQueue.DELETE_AGENT:
##                target = agent
##
##                if self._mode == NORMAL:
##                    # Remove agent from population
##
##                    try:
##                        self.agents.remove(target)
##                    except ValueError:
##                        raise SimulationError("Agent not found.")
##
##                    self.timetable.pop(target)
##                    self.num_agents -= 1
##                    self.theoretical_size -= 1
##
##                    if self.num_agents == 0:
##                        raise SimulationError("The population crashed!")
##
##                else: # CONSTANT-NUMBER MODE:
##                    # Replace with a randomly chosen agent
##
##                    if self.num_agents == 1:
##                        raise SimulationError
##
##                    try:
##                        i_target = self.agents.index(target)
##                    except ValueError:
##                        raise SimulationError("Agent not found.")
##
##                    # pick random agent to copy
##                    i_source = i_target
##                    while i_source == i_target:
##                        i_source = random.randint(0, self.num_agents-1)
##
##                    # replace target agent
##                    new_agent = self.agents[i_source].clone(); new_agent._parent = None
##                    self.agents[i_target] = new_agent
##                    self.timetable.replaceitem(target, new_agent, new_agent.next_event_time)
##                    del target
##                    self.theoretical_size -= self.theoretical_size/self.num_agents
##
##                    # Switch to normal mode if the theoretical size drops below
##                    # the constant-number threshold
####                    if self.theoretical_size < self.max_num_agents:
####                        self._mode = NORMAL



#-------------------------------------------------------------------------------
# Asynchronous Method

class AsyncMethodSimulator(BaseSimulator):


    def initialize(self):
        if self.num_agents < self.max_num_agents:
            self._mode = NORMAL
        else:
            self._mode = CONSTANT_NUMBER
        self.nbirths = 0
        self.ndeaths = 0

        # Apply user-defined initialization function.
        self._initializer(self.agents, self.world)

        # Schedule all simulation channels.
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
                    if agent.is_enabled:
                        agent.synchronize(tsync, world, q)

            # add/substitute new agents
            #self._processAgentQueue(tsync)
            replaced = set()
            while q:
                action, agent = q.dequeue()
                if self._mode == NORMAL:
                    self._processAgentNormalMode(action, agent)
                else:
                    self._processAgentConstantNumberMode(action, agent, replaced)
            replaced.clear()
            del replaced
            world.size = self.theoretical_size

            # reschedule world channels affected by agent events
            # ***NOTE: Allowing this could be problematic...
            world.crossScheduleL2GAsync(agents, pending_world_channels)

            # next world event
            world.fireNextChannel(agents, q)
            world.rescheduleDependentChannels(agents)

            # reschedule agent events affected by world event
            if world.is_modified:
                for agent in agents:
                    agent.crossScheduleG2L(world, world)

            # next sync barrier
            tsync = world.next_event_time

    def _processAgentNormalMode(self, action, agent):
            if action == AgentQueue.ADD_AGENT:
                new_agent = agent

                # Update child agent's event schedule
                new_agent.finalizePrevEvent() #removes _parent reference
                new_agent.reschedulePrevChannel(self.world)
                new_agent.rescheduleDependentChannels(self.world)

                # Add agent
                self.agents.append(new_agent)
                self.theoretical_size += 1
                self.nbirths += 1
                self.num_agents += 1

                # Switch modes if we reach the size threshold
                if self.num_agents == self.max_num_agents:
                    self._mode = CONSTANT_NUMBER

            elif action == AgentQueue.DELETE_AGENT:
                target = agent
                try:
                    self.agents.remove(target)
                except ValueError:
                    raise SimulationError("Agent not found.")

                self.theoretical_size -= 1
                self.num_agents -= 1
                self.ndeaths += 1

                if self.num_agents == 0:
                    raise SimulationError("The sample population crashed!")

    def _processAgentConstantNumberMode(self, action, agent, replaced):
        if action == AgentQueue.ADD_AGENT:
            new_agent = agent
            parent = new_agent._parent

            if parent not in replaced:
                # CONSTANT-NUMBER MODE: Substitute new agent into population

                # Update child agent's event schedule to mirror parent's
                new_agent.finalizePrevEvent()
                new_agent.reschedulePrevChannel(self.world)
                new_agent.rescheduleDependentChannels(self.world)

                # Replace a randomly chosen agent
                index = random.randint(0, len(self.agents)-1)
                replaced.add(self.agents[index])
                self.agents[index] = new_agent
                self.theoretical_size += self.theoretical_size/self.num_agents
                self.nbirths += 1

            else:
                # This agent's parent has been replaced by another agent
                # --> discard this agent
                del new_agent

        elif action == AgentQueue.DELETE_AGENT:
            target = agent
            if target not in replaced:
                # CONSTANT-NUMBER MODE: Replace deleted agent with a copy
                # of a randomly selected agent

                if self.num_agents == 1:
                    raise SimulationError

                try:
                    i_target = self.agents.index(target)
                except ValueError:
                    raise SimulationError("Agent not found.")

                # pick random agent to copy
                i_source = i_target
                while i_source == i_target:
                    i_source = random.randint(0, self.num_agents-1)

                # replace target agent
                new_agent = self.agents[i_source].clone(); new_agent._parent = None
                self.agents[i_target] = new_agent
                del target

                self.theoretical_size -= self.theoretical_size/self.num_agents
                self.ndeaths += 1

                # Switch to normal mode if the theoretical size drops below
                # the constant-number threshold
##              if self.theoretical_size < self.max_num_agents:
##                  self._mode = NORMAL
            else:
                # This agent has already been replaced --> discard
                del target







##    def _processAgentQueue(self, tsync):
##
##        replaced = set()
##
##        while self._agent_queue:
##            action, agent = self._agent_queue.dequeue()
##
##            if action == AgentQueue.ADD_AGENT:
##                self.nbirths += 1
##                new_agent = agent
##                parent = new_agent._parent
##
##                if self._mode == NORMAL:    #self.num_agents < self.max_num_agents
##                    # NORMAL MODE: Add agent to population
##
##                    # Update child agent's event schedule
##                    new_agent.finalizePrevEvent() #removes _parent reference
##                    new_agent.reschedulePrevChannel(self.world)
##                    new_agent.rescheduleDependentChannels(self.world)
##
##                    # Add agent
##                    self.agents.append(new_agent)
##                    self.theoretical_size += 1
##                    self.num_agents += 1
##
##                    # Switch modes if we reach the size threshold
##                    if self.num_agents == self.max_num_agents:
##                        self._mode = CONSTANT_NUMBER
##
##                elif parent not in replaced:
##                    # CONSTANT-NUMBER MODE: Substitute new agent into population
##
##                    # Update child agent's event schedule to mirror parent's
##                    new_agent.finalizePrevEvent()
##                    new_agent.reschedulePrevChannel(self.world)
##                    new_agent.rescheduleDependentChannels(self.world)
##
##                    # Replace a randomly chosen agent
##                    index = random.randint(0, len(self.agents)-1)
##                    replaced.add(self.agents[index])
##                    self.agents[index] = new_agent
##                    self.theoretical_size += self.theoretical_size/self.num_agents
##
##                else:
##                    # This agent's parent has been replaced by another agent
##                    # --> discard this agent
##                    del new_agent
##
##            elif action == AgentQueue.DELETE_AGENT:
##                self.ndeaths += 1
##                target = agent
##
##                if self._mode == NORMAL:
##                    # NORMAL MODE: Remove agent from population
##
##                    try:
##                        self.agents.remove(target)
##                    except ValueError:
##                        raise SimulationError("Agent not found.")
##
##                    self.theoretical_size -= 1
##                    self.num_agents -= 1
##
##                    if self.num_agents == 0:
##                        raise SimulationError("The sample population crashed!")
##
##                elif target not in replaced:
##                    # CONSTANT-NUMBER MODE: Replace deleted agent with a copy
##                    # of a randomly selected agent
##
##                    if self.num_agents == 1:
##                        raise SimulationError
##
##                    try:
##                        i_target = self.agents.index(target)
##                    except ValueError:
##                        raise SimulationError("Agent not found.")
##
##                    # pick random agent to copy
##                    i_source = i_target
##                    while i_source == i_target:
##                        i_source = random.randint(0, self.num_agents-1)
##
##                    # replace target agent
##                    new_agent = self.agents[i_source].clone(); new_agent._parent = None
##                    self.agents[i_target] = new_agent
##                    del target
##
##                    self.theoretical_size -= self.theoretical_size/self.num_agents
##
##                    # Switch to normal mode if the theoretical size drops below
##                    # the constant-number threshold
####                    if self.theoretical_size < self.max_num_agents:
####                        self._mode = NORMAL
##
##                else:
##                    # This agent has already been replaced --> discard
##                    del target
##
##        replaced.clear()
##        del replaced

