"""
Name:        save

Author:      Nezar Abdennur <nabdennur@gmail.com>
Created:     
Copyright:   (c) Nezar Abdennur 2012

"""
#!/usr/bin/env python
#-------------------------------------------------------------------------------
# These functions convert recorded data into numpy arrays and save them to disk
# in hdf5 format.
import numpy as np
import scipy.io
import h5py


def _accumulate(root):
    """
    Traverses logger tree and restructures the simulation data -- for each
    state variable, the event history of all the cells is concatenated and
    flattened into a single column of data.
    An adjacency list with index pointers (starting row, number of rows) is also
    provided so that time series data can be extracted for individual cells.
    Recording scheme originally devised by Andrei Anisenia.

    """
    adjacency_list = root.adjacencyList()
    adj_data = []
    time_data = []
    event_data = []
    names = [k for k in root.log.keys() if k != 'time' and k != 'channel']
    state_data = {name:[] for name in names}

    row = 0
    for parent, child in adjacency_list:
        pid = id(parent) if parent is not None else 0
        cid = id(child)
        num_events = len(child.log['time'])

        for name, values in child.log.items():
            if name == 'time':
                time_data.extend(values)
            elif name == 'channel':
                event_data.extend(values)
            else:
                state_data[name].extend(values)
        adj_data.append([pid, cid, row, num_events])
        row += num_events

    sim_data = {'time':time_data, 'event':event_data, 'adj':adj_data}
    sim_data['adj_info'] = ['parent_id', 'id', 'start_row', 'num_events']
    sim_data.update(state_data)
    return sim_data, names

def savemat_lineage(filename, root_node):
    sim_data, _ = _accumulate(root_node)
    scipy.io.savemat(filename, sim_data, oned_as='column')

def savehdf_lineage(filename, root_node):
    sim_data, names = _accumulate(root_node)
    with h5py.File(filename, 'w') as dfile:
        dfile = h5py.File(filename,'w')
        # Tree adjacency list
        dfile.create_dataset( name='adj_info',
                              data=np.array(sim_data['adj_info'], dtype=np.bytes_) )
        dfile.create_dataset( name='adj_data',
                              data=np.array(sim_data['adj']) )

        # Data
        dfile.create_dataset( name='time',
                              data=np.array(sim_data['time']) )
        dfile.create_dataset( name='event',
                              data=np.array(sim_data['event'], dtype=np.bytes_) )
        for name in names:
            dfile.create_dataset(name=name,
                                 data=np.array(sim_data[name]))

def savemat_snapshot(filename, recorder):
    scipy.io.savemat(filename, recorder.log, oned_as='column')

def savehdf_snapshot(filename, recorder):
    with h5py.File(filename, 'w') as dfile:
        for name, data in recorder.log.items():
            dfile.create_dataset(name=name, data=np.array(data))
