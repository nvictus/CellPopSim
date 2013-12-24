How to set up a CellPopSim model
================================

*   [Import the module](#import)
*   [Define your channels](#channels)
    *   [State-updating events](#channels-state)
    *   [Birth-death events](#channels-bd)
    *   [Manual firing](#channels-manual)
*   [Create a model object](#model)
*   [Register recorders and loggers](#recording)
*   [Run a simulation](#simulate)
*   [Saving simulation data](#saving)
*   [Additional info](#extra)

<h2 id="import">Import the module</h2>
To create a model import the `cps` module. 

```python
from cps import *
```

The `cps` module provides the following classes and functions:

- `AgentChannel`
- `WorldChannel`
- `RecordingChannel`
- `Model`
- `AMSimulator`
- `FMSimulator`
- `Recorder`
- `savemat_snapshot`
- `savemat_lineage`

The building blocks of a model are the simulation channel classes. World channel objects are assigned to the world entity while agent channel objects are assigned to agents. The cps module already provides a class called `RecordingChannel` for one type of world channel which fires at regular intervals to record snapshots of the entity collection. But the idea behind the framework is to create your own simulation channels. You do this by subclassing the `AgentChannel` or `WorldChannel` classes and overriding the methods `scheduleEvent()` and `fireEvent()`. 

<h2 id="channels">Define your channels</h2>
The schedule method must have the signature:

```python
def scheduleEvent(self, agent, world, time, source):
    ...
```

for an agent channel, or

```python
def scheduleEvent(self, world, agents, time, source):
    ...
```

for a world channel. The `time` argument is the current clock time of the parent entity. The `agents` argument is a list of all the agents currently in the collection. The `source` argument contains a reference to an agent when that agent triggers rescheduling of a world channel and is otherwise `None` -- it is deprecated and will likely be eliminated in the release version of the framework.

Fire methods have the signature:

```python
def fireEvent(self, agent, world, time, event_time, ...):
    ...
```

for an agent channel, or

```python
def fireEvent(self, world, agents, time, event_time, ...):
   ...
```

for a world channel. The `event_time` is the firing time of the event being fired. After the fire method returns, the parent entity's clock is advanced to that time. The fire method can also provide any number of custom keyword arguments after the fifth one (e.g., using the python `**kwargs` construct), which can be used to pass extra information to the channel when it is fired [manually](#channels-manual).

<h3 id="channels-state">State-updating events</h3>

A state-updating event is any simulation event that may cause a change in an entity's state. A toy example is a simple counting process that increments a counter at random intervals. The class would look like:

```python
class PoissonProcessChannel(AgentChannel):
""" Simulates a counting process """
    def __init__(self, rate):
        self.rate = rate

    def scheduleEvent(self, agent, world, time, src):
        return time - math.log(random.uniform(0,1))/self.rate

    def fireEvent(self, agent, world, time, event_time):
        agent.count += 1
        return True
```

This is an example of a channel with a discrete-updating pattern of execution. Other channels may update a continuous variable or a variable that depends on a continuous quantity. For example, lets say that cell division depends on a cell's volume surpassing a threshold level, but the volume evolves in an unpredictable manner. We could write a channel class to handle this:

```python
class CellDivisionChannel(AgentChannel):
""" Cell divides when volume crosses threshold """
    def __init__(self, tstep, vt):
        self.tstep = tstep
        self.v_threshold = vt

    def scheduleEvent(self, agent, world, time, src):
        return time + self.tstep

    def fireEvent(self, agent, world, time, event_time):
        if agent.volume >= self.v_threshold:
            new_agent = self.cloneAgent(agent)
            agent.volume /= 2
            new_agent.volume /= 2
            return True
        else:
            return False
```

When the cell called `agent` reaches the threshold volume, it is cloned. Note the use of the channel's inherited `cloneAgent()` method to produce a copy called `new_agent` of the cell called `agent`. The volumes of the two cells are then halved before the channel's fire method returns. If the volume is subthreshold nothing occurs and so we return `False` so that the simulator does not invoke rescheduling dependencies.

<h3 id="channels-bd">Birth-death events</h3>

The use of `cloneAgent()` is what we call a birth event, which is intended to introduce a new agent into the collection. We can also remove an agent from the collection by calling the `killAgent()` method. 

The actual outcome of cloning or killing agents depends on the size of the collection. When simulating in __normal__ mode, the agents are simply added or removed from the internal agents data structure. However, when simulating in __constant-number__ mode, there is the additional side effect of 1) removing a randomly chosen agent when a new one is added and 2) copying a randomly chosen agent when one is removed.

By default, the simulation runs in __normal__ mode when the number of agents in the collection is less than the maximum set number and switches to __constant-number__ mode as soon as these two numbers are equal.

<h3 id="channels-manual">Manual firing</h3>

You can fire a channel from within another channel by using the channel method `fire()`. For example, in our counting process above, we might want to fire another channel to update the cell volume to keep the two variables synchronized:
```python
class PoissonProcessChannel(AgentChannel):
	...

    def fireEvent(self, agent, world, time, event_time):
		self.fire(agent, 'UpdateVolumeChannel')
        agent.count += 1
        return True
```
The manually fired channel receives the same values of `time` and `event_time` as those of the channel that fired it. Of course, if `UpdateVolumeChannel` uses a sufficiently small time step, these manual firings would not be necessary. Another application of manual firing is to modify an agent from within a world channel or for an agent channel to modify the world entity. There is an extra `reschedule` option which is `False` by default when a channel is manually fired. If the `reschedule` option is set to `True`, then after the agent (world) channel fires, its dependent agent (world) channels will be rescheduled. Also, additional keyword arguments can be passed to a channel being fired manually, provided the channel's `fireEvent()` method accepts those arguments in its function signature.


<h2 id="model">Create a model object</h2>
The ingredients of a model are:

1. The __initial number__ of agents to create and __maximum number__ to allow
2. A set of __world channel__ and __agent channel__ objects and their __rescheduling dependencies__
3. An __initializer__ to set the initial state of the agents and world
4. __Recorders__ and __loggers__ to collect data

We can create an empty model object by calling the `Model` class constructor as follows:
```python
my_model = Model(n0=100, nmax=1000)
```
where the `n0` and `max` arguments are the initial and maximum number of agents in the collection, respectively.

We then create instances of each of our defined channel classes. We need to provide at least one world channel object for the simulation to work. For example, the `RecordingChannel` constructor takes a recorder object and the value of the time step between recordings as input arguments:
```python
rec_channel = RecordingChannel(recorder, 70)
```

Then we add each channel object to the model using the methods `addWorldChannel()` and `addAgentChannel()`. __Rescheduling dependencies__ can be specified by passing in sequences for the  `ac_dependents` and/or `wc_dependents` arguments.

```python
my_model.addAgentChannel(c3, ac_dependents=[c2,c4], wc_dependents=[c1])
```

Every agent will obtain a unique copy of the agent channel objects you created. In the above example, each time an agent's channel _c3_ fires and is subsequently rescheduled, its channels _c2_ and _c4_ and the world channel _c1_ will be automatically rescheduled by the simulator. The rescheduling occurs in the order: _c3_, _c2_, _c4_, _c1_. A last optional argument when adding agent channels is the `sync` option which is `False` by default. If changed to `True`, the agent channel _c3_ is considered to be a _sync-channel_ which means that the simulator will fire it right before every world channel fires. This is normally useful for synchronization purposes, hence the name.

When adding a world channel as in the following example,
```python
my_model.addWorldChannel(w7, ac_dependents=[c2,c3,c4], wc_dependents=[w1,w2])
```
this means that each time _w7_ fires, first _w7_ gets rescheduled, then the world channels _w1_ and _w2_ get rescheduled. Finally, the agent channels _c2_, _c3_ and _c4_ are rescheduled in every agent in the collection.

We also need to include an __initializer__. This is just a function we write to set the initial state of each of the agents and the world. An example would look like:

```python
def my_initializer(world, agents):
    # initialize world entity
    world.stress = False
    world.Kw = 2
    world.nw = 100
	# initialize the cells
    for cell in agents:
        cell.alive = True
        cell.x = math.sqrt(0.5*10*0.1)*random.normalvariate(0,1)
        cell.y = math.exp(cell.x)
```

We add the initializer function to the model, first providing a list of the names of the world state variables and then a list of agent state variable names and then the initializer function:
```python
my_model.addInitializer(['stress', 'Kw', 'nw'], ['alive', 'x', 'y'], my_initializer)
```

<h2 id="recording">Register recorders and loggers</h2>
The framework currently provides two built-in ways of recording data during a simulation run. The first is an object called a __recorder__ which takes snapshots of all the entities by default. The second is an object called a __logger__, which is attached to a specific agent and records the state of that agent after each firing of its channels. The logger also branches when an agent is cloned and records the history of child agents as well. In other words, a logger stores a tree of nodes containing the event history of the agents in a genealogical lineage. Both recorders and loggers can be customized.

### Recorders
To create a recorder, use the `Recorder` class and provide the names of the world state variables to record and then the names of agent state variables to record. Optionally you can include a custom recording function as a third argument.

```python
recorder = Recorder(['stress'], ['alive','x','y','capacity'], my_recorder)
my_model.addRecorder(recorder)
```

By default the recorder records all the variables listed without any pre-processing. If you want to define your own recording function (called `my_recorder` in the example), it should look something like:

```python
def my_recorder(log, time, world, agents):
    log['stress'].append(world.stress)
    log['alive'].append([agent.alive for agent in agents])
    log['capacity'].append([agent.capacity for agent in agents])
    log['x'].append([agent.x for agent in agents])
    log['y'].append([agent.y for agent in agents])
```

where `log` is a dictionary where each name you provided in the `Recorder` constructor is mapped to a list. In this example, each world variable is appended to the list with the same name. For each agent variable, the values belonging to all the agents are grouped together using a [list comprehension](http://docs.python.org/py3k/tutorial/datastructures.html#list-comprehensions) over all the agents and appended to produce a list of lists. The default recording method does something similar to what is shown in the example above. The recording time is logged automatically.

### Loggers
To attach a logger to a cell lineage, specify an index between `0` and `n0-1` referring to one of the agents at the beginning of the simulation. After that, specify a list of names for the log, optionally followed by a logger function.

```python
model.addLogger(0, ['alive','x','y'], my_logger)
```

The default logger function tries to copy and append the state variables each time an agent channel fires. A custom logger function would look something like:

```python
def my_logger(log, time, agent):
    log['alive'].append(agent.alive)
    log['x'].append(agent.x)
    log['y'].append(agent.y)
```

where again, `log` is a dictionary mapping names to lists. The time of each event and id of the channel that fired are also recorded to the log automatically. After a simulation, a logger provides methods to traverse the nodes of the agent lineage using breadth-first or depth-first search algorithms. See the docs in the `cps.logging` submodule for more information.

<h2 id="simulate">Run a simulation</h2>
To run a simulation there are two possible algorithms you can use:

1. The _First-Entity method_ (FM)
2. The _Asynchronous method_ (AM)

corresponding to two simulator classes `FMSimulator` and `AMSimulator`.

In both cases the process is the same. First, you create a simulator by calling the simulator constructor, passing in the model object and the initial time as input arguments. Then you can (iteratively, if you like) call the `runSimulation()` method with the terminal time. Note that the AM simulation algorithm does not support certain types of firing and rescheduling.

```python
sim = AMSimulator(my_model, 0)
sim.runSimulation(500)
```

References to each of the loggers and recorders you added are stored in lists called `loggers` and `recorders`, respectively, in the simulator object.

<h2 id="saving">Saving simulation data</h2>
I included two functions to save the recorder and logger data logs to MATLAB mat files, as well as similar functions to save to HDF5 format. Let's stick to the mat format and assume we're saving to some file with given path strings:

```python
savemat_lineage(some_file_path, sim.loggers[2])
savemat_snapshot(another_file_path, sim.recorders[0])
```

The `savemat_lineage` function saves logger data. For each agent state variable, the data from each individual cell is concatenated a long array and a separate matrix called `adj` stores the indices that demark the range of data belonging to each cell, along with a adjacency list of node ids so that the tree can be reconstructed.

The `savemat_snapshot` function is for recorder data. If the simulation has _N_ cells throughout and _T_ recording events, the snapshot data file will contain a _TxN_ matrix for each numerical state variable along with a _Tx1_ vector of time points. If the size of the collection changes during simulation, the state data will be saved in _Tx1_ cell arrays.

<h2 id="extra">Additional info</h2>
### Tracking the virtual population density
[This feature is still "hidden" and needs to be refactored and properly exposed]

When running a simulation in __constant-number__ mode, it is useful to think of the collection as a coarse-grained representation of a virtual population in a fixed volume. Currently, we use two hidden world attributes --- lists called `_size` and `_ts` --- to monitor this virtual population size over time. When the agent queue is non-empty, each time it is processed the new estimate of the virtual population size is appended to the `world._size` list and the time stamp is appended to `world._ts`. 

When constant-number mode is initiated, we have `world._size[-1] == nmax`. We consider each agent to "represent" `world._size[-1]/nmax` virtual agents, so when a new agent is introduced/eliminated from the collection, we increment/decrement `world._size[-1]` by that amount to obtain our new value. The `world._size` data can later be rescaled to denote a concentration or density of individuals.
