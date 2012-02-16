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
from entities import *
import random

class FEMethodManager(Manager):
    def __init__(self, init_num_agents, max_num_agents, tstart, model):
        self.num_agents = init_num_agents
        self.max_num_agents = max_num_agents

        #create objects
        self.world = self._createWorld(tstart,
                                       model.world_vars,
                                       model.world_channels,
                                       model.world_dep_graph)
        self.agents = self._createAgents(init_num_agents,
                                         tstart,
                                         model.agent_vars,
                                         model.agent_channels,
                                         model.agent_dep_graph)
        self._add_queue = AgentQueue()
        self._rem_queue = AgentQueue()

        #initialize
        model.init_fcn(self.agents, self.world, model.parameters)
        self.timetable = self._initializeTimetable() #indexed priority queue

    def runSimulation(self, tstop):
        aq = self._add_queue
        rq = self._rem_queue
        agents = self.agents
        world = self.world

        # get earliest event and engine
        tmin, emin = self.timetable.peekMin()

        while (tmin <= tstop):
            if emin is world:
                # TODO:synchronize local engines (fire gap channels)

                # fire global event and advance clock
                world.fireNextChannel(agents, aq, rq) #!!!!!!

                if not world._enabled:
                    return # premature termination

                # reschedule last global channel and dependent channels
                new_time = world.rescheduleChannels(agents) #!!!!!!
                self.timetable.update(world, new_time)

                # TODO:fire global gap channels

                # reschedule ALL channels of active local engines
                for agent in agents:
                    new_time = agent.scheduleAllChannels(world) #!!!!!!
                    self.timetable.update(agent, new_time)
                    #Note: could introduce some way to prevent total
                    #      rescheduling here
                    #Todo: skip this if global event and gap
                    #      closure produced no modification!

            else: #emin is an agent

                # fire event and advance clock
                emin.fireNextChannel(world, aq, rq) #!!!!!!

                # reschedule last channel and dependent channels
                new_time = emin.rescheduleChannels(world) #!!!!!!
                self.timetable.update(emin, new_time)

                # TODO:fire gap channels and reschedule

                if not emin._enabled:
                    # don't delete engine! we still may want to record its data
                    pass

            # get earliest event and engine
            tmin, emin = self.timetable.peekMin()

            # add/substitute new engines and cells
            self._processAgentQueues()
        #endwhile

    def _initializeTimetable(self):
        time = self.world.scheduleAllChannels(self.agents) #!!!!!!
        event_times = [time]
        entities = [self.world]
        for agent in self.agents:
            time = agent.scheduleAllChannels(self.world) #!!!!!!
            event_times.append(time)
            entities.append(agent)
        return IndexedPriorityQueue(entities, event_times)

    def _processAgentQueues(self):
        while not self._add_queue.isEmpty():
            _, new_agent = self._add_queue.popAgent()
            # reschedule to get next event time
            time, _ = new_agent.rescheduleChannels(self.world) #!!!!!!
            if self.num_agents < self.max_num_agents:
                # add to manager
                self.agents.append(new_agent)
                # add to ipq
                self.timetable.add(new_agent, time)
                self.num_agents += 1
            else:
                index = random.randint(0, len(self.agents)-1)
                target_agent = self.agents[index]
                # substitute in manager
                self.agents[index] = new_agent
                # substitute in ipq
                self.timetable.replace(target_agent, new_agent, time)
                del target_agent

    def _createAgents(self, num_agents, t0, state_variables, channels, dep_graph):
        agents = []
        for i in range(num_agents):
            copied_channels = {}
            for channel in channels:
                copied_channels[channel] = copy(channel)

            copied_dep_graph = {}
            for channel in channels:
                dependencies = dep_graph[channel]
                copied_dep_graph[copied_channels[channel]] = (copied_channels[dependency] for dependency in dependencies)

            state = State(state_variables)
            engine = ACEngine(t0, copied_channels.values(), copied_dep_graph)
            agents.append(Agent(state, engine))
        return agents

    def _createWorld(self, t0, state_variables, channels, dep_graph):
        state = State(state_variables)
        engine = WCEngine(t0, channels, dep_graph)
        return World(state, engine)








class Model(object):
    pass


import time
from channels import *

def main():
    s = ((1, 0), (0, 1), (-1, 0), (0, -1))
    prop_fcn = lambda x, p: [ p.kR, p.kP*x[0], p.gR*x[0], p.gP*x[1] ]
    ch1 = GillespieChannel(propensity_fcn=prop_fcn, stoich_list=s)
    ch2 = AgentChannel()

    m = Model()
    m.world_vars = ('kR', 'kP', 'gR', 'gP')
    m.world_channels = []
    m.world_dep_graph = {}
    m.agent_vars = ('x',)
    m.agent_channels = [ch1,ch2]
    m.agent_dep_graph = {ch1:(ch2,), ch2:(ch1,)}
    m.parameters = {'kR':0.1, 'kP':0.1, 'gR':0.1, 'gP':0.002}
    def init_fcn(cells, gdata, params):
        gdata.state.kR = params['kR']
        gdata.state.kP = params['kP']
        gdata.state.gR = params['gR']
        gdata.state.gP = params['gP']
        for cell in cells:
            cell.state.x = [0,0]
    m.init_fcn = init_fcn

    mgr = FEMethodManager(10, 10, 0, m)
    t0 = time.time()
    mgr.runSimulation(10000.0)
    t = time.time()
    print(t-t0)


    print()

if __name__ == '__main__':
    main()