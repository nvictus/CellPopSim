#!/usr/bin/env python
#-------------------------------------------------------------------------------
# These functions convert recorded data into numpy arrays and save them to disk
# in hdf5 format.
import numpy as np
import h5py

def save_snapshot(filename, recorder):
    """
    Assumes recorder has a field named "time" and the other recorded state
    variables can be converted directly into numpy arrays.

    """
    try:
        dfile = h5py.File(filename, 'w')
        dfile.create_dataset(name='time', data=np.array(recorder.time))
        dfile.create_dataset(name='size', data=np.array(recorder.size))
        for dname in recorder.getFields():
            dfile.create_dataset(name=dname, data=np.array(getattr(recorder, dname)))

    finally:
        dfile.close()


def save_lineage(filename, root_node, var_names):
    """
    Traverses datalog tree and restructures the simulation data -- for each
    state variable, the event history of all the cells is concatenated and
    flattened into a single column of data.
    An adjacency list with index pointers (starting row, number of rows) is also
    provided so that time series data can be extracted for individual cells.
    Recording scheme originally devised by Andrei Anisenia.

    """
    adj_list = root_node.traverse()
    tstamp = []
    estamp = []
    data = []
    output_adj_list = []

    row = 0
    for parent, child in adj_list:
        pid = id(parent) if parent is not None else 0
        cid = id(child)

        tstamp.extend(child.tstamp)
        estamp.extend(child.estamp)
        data.extend(child.log)

        output_adj_list.append([pid, cid, row, len(child.log)])
        row += len(child.log)

    try:
        dfile = h5py.File(filename,'w')
        # Tree adjacency list
        dfile.create_dataset(name='adj_info',
                             data=np.array(['parent_id',
                                            'id',
                                            'start_row',
                                            'num_events'], dtype=np.bytes_))
        dfile.create_dataset(name='adj_data',
                             data=np.array(output_adj_list))

        # Log of time and event type
        dfile.create_dataset(name='time',
                             data=np.array(tstamp))
        dfile.create_dataset(name='event',
                             data=np.array(estamp, dtype=np.bytes_))

        # Data values
        dfile.create_dataset(name='state_info',
                             data=np.array(var_names, dtype=np.bytes_))
        dfile.create_dataset(name='state_data',
                             data=np.array(data))
    finally:
        dfile.close()
