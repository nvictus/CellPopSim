"""
Name:        simulator

Author:      Nezar Abdennur <nabdennur@gmail.com>
Created:     23/04/2012
Copyright:   (c) Nezar Abdennur 2012

"""
#!/usr/bin/env python
from cps.misc import IndexedPriorityQueue
from cps.exception import ZeroPopulationError, SimulationError
import random

NORMAL = 0
CONSTANT_NUMBER = 1


class BaseSimulator(object):
    """
    Base class for simulators.

    Attributes:
        num_agents       (int)
        num_agents_max   (int)
        world            (cps.entity.World)
        agents           (list-of-cps.entity.Agent)
        agent_queue      (cps.misc.AgentQueue)
        loggers          (list-of-cps.state.LoggerNode)
        recorders        (list-of-cps.state.Recorder)

    """
    def __init__(self, model, tstart):
        """
        Initialize a simulator according to the specification of the provided
        model.

        """
        from cps.model import create_world, create_agents

        # keep count of agents
        self.num_agents = model.n0
        self.num_agents_max = model.nmax

        # create world entity
        self.world = create_world(model, self, tstart)

        # create agent entities
        self.agents = create_agents(model, self, tstart)

        # loggers
        self.loggers = []
        for i in sorted(model.logged):
            self.loggers.append(self.agents[i]._logger)

        # recorders
        self.recorders = model.recorders

        # initialization routine
        self.state_initializer = model.initializer

        # create queue
        self.agent_queue = model.AgentQueueType()

        self._do_sync = any([entry.sync for entry in model.agent_channel_table.values()])

        self.initialize()

    def initialize(self):
        raise NotImplementedError

    def runSimulation(self, tstop):
        raise NotImplementedError

    def finalize(self):
        raise NotImplementedError



#-------------------------------------------------------------------------------
# First-Entity (synchronous) Method

class FMSimulator(BaseSimulator):

    def initialize(self):
        self._mode = NORMAL if self.num_agents < self.num_agents_max else CONSTANT_NUMBER
        self._processAgent = {NORMAL:self._processAgentNormalMode,
                              CONSTANT_NUMBER:self._processAgentConstantNumberMode}
        self.sizethresh_hi = self.num_agents_max
        self.sizethresh_lo = -1
        self.world._ts = [self.world._time]
        self.world._size = [self.num_agents]
        self.nbirths = 0
        self.ndeaths = 0

        # initialize state variables with user-defined function
        self.state_initializer(self.world, self.agents)

        # schedule simulation channels
        self.world._scheduleAllChannels()
        for agent in self.agents:
            agent._scheduleAllChannels()

        # set up global timetable
        event_times = [agent._next_event_time for agent in self.agents]
        self.timetable = IndexedPriorityQueue(zip(self.agents, event_times))

        # TODO: make this better
        for recorder in self.recorders:
            recorder.record(self.world._time, self.world, self.agents)

    def runSimulation(self, tstop):
        world = self.world
        agents = self.agents
        timetable = self.timetable

        emin, tmin = self._earliestItem()

        while (tmin <= tstop):
            if emin is world:
                # fire agent sync channels
                if self._do_sync:
                    for agent in agents:
                        agent._synchronize(tmin)
                        if agent in timetable:
                            timetable.updateitem(agent, agent._next_event_time)
                    emin, tmin = self._earliestItem()
                    if emin is not world:
                        continue

                # fire next world channel
                world._processNextChannel() #processes queue
                #timetable.updateitem(world, world.next_event_time)

                if world._is_modified:
                    for agent in agents:
                        agent._rescheduleFromWorld(world)
                        timetable.updateitem(agent, agent._next_event_time)

                # if world was stopped, terminate simulation
                if not world._enabled:
                    self.finalize()
                    return

            elif not emin._enabled:
                # if agent was stopped or killed, remove from global timetable
                del timetable[emin]

            else:
                # fire next agent channel
                emin._processNextChannel() #processes queue
                if emin in timetable:
                    if not emin._enabled:
                        del timetable[emin]
                    else:
                        timetable.updateitem(emin, emin._next_event_time)
                        if emin._is_modified:
                            world._rescheduleFromAgent(emin)
                            #timetable.updateitem(world, world.next_event_time)

            emin, tmin = self._earliestItem()

        self.finalize()

    def finalize(self):
        pass

    def _earliestItem(self):
        world, t_world = self.world, self.world._next_event_time
        agent, t_agent = self.timetable.peek()
        if t_agent <= t_world:
            return agent, t_agent
        else:
            return world, t_world

    def _processAgentQueue(self):
        q = self.agent_queue
        size = self.world._size[-1]
        while q:
            action, agent = q.dequeue()
            size += self._processAgent[self._mode](action, agent)
            # Switch modes if we reach the size threshold
            if self._mode == NORMAL and self.num_agents == self.sizethresh_hi:
                self._mode = CONSTANT_NUMBER
            # Switch modes if we drop to or below the size threshold
            elif self._mode == CONSTANT_NUMBER and size <= self.sizethresh_lo:
                size = self.self.sizethresh_lo
                self._mode = NORMAL
        self.world._ts.append( self.world._time )
        self.world._size.append( size )

    def _processAgentNormalMode(self, action, agent):
        agents = self.agents
        timetable = self.timetable
        q = self.agent_queue
        if action == q.ADD_AGENT:
            new_agent = agent
            new_agent._parent = None
            agents.append(new_agent)
            timetable.add(new_agent, new_agent._next_event_time)
            self.num_agents += 1
            self.nbirths += 1
            return 1
        elif action == q.DELETE_AGENT:
            target = agent
            try:
                agents.remove(target)
            except ValueError:
                raise SimulationError("Agent not found.")
            timetable.pop(target)
            self.num_agents -= 1
            # Raise error if sample population crashes
            if self.num_agents == 0:
                raise ZeroPopulationError("The population crashed!")
            self.ndeaths += 1
            return -1

    def _processAgentConstantNumberMode(self, action, agent):
        agents = self.agents
        world = self.world
        timetable = self.timetable
        q = self.agent_queue
        if action == q.ADD_AGENT:
            new_agent = agent
            new_agent._parent = None
            # Choose a random agent to replace
            index = random.randint(0, len(self.agents)-1)
            target = agents[index]
            # Substitute new agent into agent list and ipq
            agents[index] = new_agent
            try:
                timetable.replaceitem(target, new_agent, new_agent._next_event_time)
            except KeyError:
                timetable.add(new_agent, new_agent._next_event_time) #target may be inactivated and no longer in the ipq
            del target
            self.nbirths += 1
            return world._size[-1]/self.num_agents_max
        elif action == q.DELETE_AGENT:
            # This shouldn't happen...
            if self.num_agents <= 1:
                raise SimulationError
            # Find target agent in the agent list
            target = agent
            try:
                i_target = agents.index(target)
            except ValueError:
                raise SimulationError("Agent not found.")
            # Choose a random agent to copy
            i_source = i_target
            while i_source == i_target:
                i_source = random.randint(0, self.num_agents-1)
            # Replace target agent with the copy
            new_agent = agents[i_source].__copy__()
            agents[i_target] = new_agent
            if new_agent._enabled:
                timetable.replaceitem(target, new_agent, new_agent._next_event_time) #will fail if cell is killed twice!
            del target
            self.ndeaths += 1
            return -(world._size[-1]/self.num_agents_max)





#-------------------------------------------------------------------------------
# Asynchronous Method

class AMSimulator(BaseSimulator):

    def initialize(self):
        self._mode = NORMAL if self.num_agents < self.num_agents_max else CONSTANT_NUMBER
        self.sizethresh_hi = self.num_agents_max
        self.sizethresh_lo = -1
        self.world._ts = [self.world._time]
        self.world._size = [self.num_agents]
        self.nbirths = 0
        self.ndeaths = 0
        self._replaced = set()

        # Apply user-defined initialization function.
        self.state_initializer(self.world, self.agents)

        # Schedule all simulation channels.
        self.world._scheduleAllChannels()
        for agent in self.agents:
            agent._scheduleAllChannels()

    def runSimulation(self, tstop):
        world = self.world
        agents = self.agents

        #self._do_sync= False
        tsync = world._next_event_time

        while (tsync <= tstop):
            not_done = agents
            while not_done:
                for agent in not_done:
                    while agent._enabled and agent._time <= tsync:
                        agent._processNextChannel() #does not process queue
                    if self._do_sync:
                        agent._synchronize(tsync)   #does not process queue
                # process queue late
                not_done = self._processAgentQueue()

            # TODO: cross-schedule A2W from a collected batch of dependents
            # NOTE: agent-to-world scheduling could be a BAD idea

            # fire next world channel
            world._processNextChannel() #processes queue

            # if world was stopped, terminate simulation
            if not world._enabled:
                self.finalize()
                return

            if world._is_modified:
                for agent in agents:
                    agent._rescheduleFromWorld(world)

            tsync = world._next_event_time

        if tsync > tstop:
            not_done = agents
            while not_done:
                for agent in not_done:
                    while agent._enabled and agent._time <= tstop:
                        agent._processNextChannel() #does not process queue
                    if self._do_sync:
                        agent._synchronize(tstop)   #does not process queue
                # process queue late
                not_done = self._processAgentQueue()

        self.finalize()

    def finalize(self):
        pass

    def _processAgentQueue(self):
        q = self.agent_queue
        not_done = set()
        replaced = self._replaced
        # Process agents one by one
        size = self.world._size[-1]
        while q:
            action, agent = q.dequeue()
            if self._mode == NORMAL:
                size += self._processAgentNormalMode(action, agent, not_done)
                # Switch modes if we reach the size threshold
                if self.num_agents == self.sizethresh_hi:
                    self._mode = CONSTANT_NUMBER
            else:
                size += self._processAgentConstantNumberMode(action, agent, not_done, replaced)
                # Switch modes if we fall to or drop below the size threshold
                if size <= self.sizethresh_lo:
                    size = self.sizethresh_lo
                    self._mode = NORMAL
        # Update population counter
        self.world._ts.append( self.world._time )
        self.world._size.append( size )
        # Clear memo of replaced agents
        if replaced:
            replaced.clear()
        # Return successfully added agents
        return not_done

    def _processAgentNormalMode(self, action, agent, not_done):
        agents = self.agents
        q = self.agent_queue
        if action == q.ADD_AGENT:
            agent._parent = None
            agents.append(agent)
            self.num_agents += 1
            self.nbirths += 1
            not_done.add(agent)
            return 1
        elif action == q.DELETE_AGENT:
            target = agent
            try:
                agents.remove(target)
            except ValueError:
                raise SimulationError("Agent not found.")
            self.num_agents -= 1
            if self.num_agents == 0:
                raise ZeroPopulationError("The sample population crashed!")
            self.ndeaths += 1
            return -1

    def _processAgentConstantNumberMode(self, action, agent, not_done, replaced):
        agents = self.agents
        world = self.world
        q = self.agent_queue
        if action == q.ADD_AGENT:
            parent = agent._parent
            agent._parent = None
            if parent not in replaced:
                # Choose a random agent to replace, keep note of its replacement
                index = random.randint(0, len(self.agents)-1)
                replaced.add(agents[index])
                # Substitute new agent into the list
                agents[index] = agent
                self.nbirths += 1
                not_done.add(agent)
                return world._size[-1]/self.num_agents_max
            else:
                # This agent's parent has been replaced by another agent at an earlier time.
                # Discard this agent!
                return 0
        elif action == q.DELETE_AGENT:
            target = agent; del agent
            if target not in replaced:
                # NOTE: This should not be allowed in CN mode.
                if self.num_agents == 1:
                    raise SimulationError
                # Find target agent in the agent list
                try:
                    i_target = agents.index(target)
                except ValueError:
                    raise SimulationError("Agent not found.")
                # Choose random agent to copy
                i_source = i_target
                while i_source == i_target or not agents[i_source]._enabled:
                    i_source = random.randint(0, self.num_agents-1)
                # Replace target agent
                agents[i_target] = agents[i_source].__copy__()
                del target
                self.ndeaths += 1
                return -(world._size[-1]/self.num_agents_max)
            else:
            # This agent's parent has been replaced by another agent at an earlier time.
            # Discard this agent!
                return 0



