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
from event import Agent, LineageAgent, World, create_agent, create_world
from misc import *
import random


class AbstractManager(object):
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
            root_nodes (list-of-LineageNode)
            add_queue (AgentQueue)
            rem_queue (AgentQueue)

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

        # create queues
        self._add_queue = AgentQueue()
        self._rem_queue = AgentQueue()

    def initialize(self):
        raise(NotImplementedError)

    def runSimulation(self, tstop):
        raise(NotImplementedError)


class FEMethodManager(AbstractManager):
    def __init__(self, model, tstart):
        """
        Attributes:
            num_agents (int)
            max_num_agents (int)
            world (World)
            agents (list-of-Agent)
            add_queue (AgentQueue)
            rem_queue (AgentQueue)
            timetable (IndexedPriorityQueue)

        """
        super(FEMethodManager, self).__init__(model, tstart)

        # initialize entities
        self.initialize(model)

        # set up global timetable
        event_times = [self.world.next_event_time]
        entities = [self.world]
        for agent in self.agents:
            event_times.append(agent.next_event_time)
            entities.append(agent)
        self.timetable = IndexedPriorityQueue(entities, event_times)

    def initialize(self, model):
        """
        Apply user-defined initialization function and schedule all simulation
        channels.

        """
        # initialize state variables with user-defined function
        model.init_fcn(self.agents, self.world, model.parameters)
        # schedule simulation channels
        self.world.scheduleAllChannels(self.agents)
        for agent in self.agents:
            agent.scheduleAllChannels(self.world)

    def runSimulation(self, tstop):
        """
        Perform a simulation from initial simulation clock time until tstop.
        The algorithm is called the First-Entity Method.

        """
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
                    agent.closeGaps(tmin, world, aq, rq)
                    self.timetable.update(agent, agent.next_event_time)

                # next world event
                world.fireNextChannel(agents, aq, rq)
                world.rescheduleDependentChannels(agents)
                world.closeGaps(tmin, agents, aq, rq)
                self.timetable.update(world, world.next_event_time)
                if not world._enabled: # terminate simulation prematurely
                    return

                # reschedule agent channels affected by world event
                if world.is_modified:
                    for agent in agents:
                        agent.rescheduleAux(world, world)
                        self.timetable.update(agent, agent.next_event_time)

            elif emin._enabled:      #(emin is an agent)
                # next agent event
                emin.fireNextChannel(world, aq, rq)
                emin.rescheduleDependentChannels(world)
                self.timetable.update(emin, emin.next_event_time())

                # reschedule world channels affected by agent event
                if emin.is_modified:
                    world.rescheduleAux(agents, emin)
                    self.timetable.update(world, world.next_event_time)

             # add/substitute new agents
            self._processAgentQueues(tmin)

            # get earliest event and entity
            tmin, emin = self.timetable.peekMin()
        #endwhile

    def _processAgentQueues(self, tbarrier):
        while not self._add_queue.isEmpty():
            parent, new_agent = self._add_queue.popAgent()

            # Update child agent's schedule to mirror parent's
            # finalize the event added this agent to the queue
            new_agent.finalizePrevEvent(parent)
            new_agent.reschedulePrevChannel(self.world)
            new_agent.rescheduleDependentChannels(self.world)
            #no need to fire gap channels!

            # Add or substitute new agent
            if self.num_agents < self.max_num_agents:
                # add to manager
                self.agents.append(new_agent)
                # add to ipq
                self.timetable.add(new_agent, new_agent.next_event_time)
                self.num_agents += 1
            else:
                index = random.randint(0, len(self.agents)-1)
                target_agent = self.agents[index]
                # substitute in manager
                self.agents[index] = new_agent
                # substitute in ipq
                self.timetable.replace(target_agent, new_agent, new_agent.next_event_time)
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
        """
        Apply user-defined initialization function and schedule all simulation
        channels.

        """
        model.init_fcn(self.agents, self.world, model.parameters)
        self.world.scheduleAllChannels(self.agents)
        for agent in self.agents:
            agent.scheduleAllChannels(self.world)

    def runSimulation(self, tstop):
        """
        Perform a simulation from initial simulation clock time until tstop.
        The algorithm is called the Asynchronous Method.

        """
        aq = self._add_queue
        rq = self._rem_queue
        agents = self.agents
        world = self.world

        tsync = world.next_event_time

        while (tsync <= tstop):
            # release agents to sync time barrier
            pending_world_channels = set()
            for agent in agents:
                    clock = agent.next_event_time
                    while agent._enabled and clock <= tsync:
                        agent.fireNextChannel(world, aq, rq)

                        # collect affected world channels
                        wcs = agent.getDependentWorldChannels()
                        if wcs and world.is_modified:
                            for wc in wcs:
                                pending_world_channels.add(wc)

                        agent.rescheduleDependentChannels(world)
                        clock = agent.next_event_time
                    agent.closeGaps(tsync, world, aq, rq)

            # add/substitute new agents
            self._processAgentQueues(tsync)

            # reschedule world channels affected by agent events
            world.rescheduleAuxAsync(agents, pending_world_channels)

            # next world event
            world.fireNextChannel(agents, aq, rq)
            world.rescheduleDependentChannels(agents)
            world.closeGaps(tsync, agents, aq, rq)

            # reschedule agent events affected by world event
            if world.is_modified:
                for agent in agents:
                    agent.rescheduleAux(world, world)

            # next sync barrier
            tsync = world.next_event_time

    def _processAgentQueues(self, tsync):
        targets = set()
        while not self._add_queue.isEmpty():
            parent, new_agent = self._add_queue.popAgent()

            # Add or substitute new agent
            if self.num_agents < self.max_num_agents:
                # Update child agent's event schedule to mirror parent's
                new_agent.finalizePrevEvent(parent)
                new_agent.reschedulePrevChannel(self.world)
                new_agent.rescheduleDependentChannels(self.world)
                new_agent.closeGaps(tsync, self.world, self._add_queue, self._rem_queue)

                # Add agent
                self.agents.append(new_agent)
                self.num_agents += 1
            elif parent not in targets:
                # Update child agent's event schedule to mirror parent's
                new_agent.finalizePrevEvent(parent)
                new_agent.reschedulePrevChannel(self.world)
                new_agent.rescheduleDependentChannels(self.world)
                new_agent.closeGaps(tsync, self.world, self._add_queue, self._rem_queue)

                # Replace a randomly chosen agent
                index = random.randint(0, len(self.agents)-1)
                targets.add(self.agents[index])
                self.agents[index] = new_agent
            else:
                # This agent's parent has been replaced by another agent
                # --> discard this agent
                del new_agent

        if targets:
            for target in targets:
                del target
            del targets




def main():
    pass

if __name__ == '__main__':
    main()
