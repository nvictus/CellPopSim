"""
Copyright (C) 2012, Nezar Abdennur <nabdennur@gmail.com>

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met: 

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer. 
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution. 

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

Dynamical Systems Biology Laboratory
www.sysbiolab.uottawa.ca

"""
#!/usr/bin/env python

# Required
from cps.channel import AgentChannel, WorldChannel
from cps.logging import Recorder
from cps.model import Model
from cps.simulator import FMSimulator, AMSimulator

# Channels
from cps.channel import RecordingChannel

# Exception handling
from cps.exception import SimulationError, SchedulingError, ZeroPopulationError

# Functions for saving recorder and logger data to file
from cps.save import savemat_snapshot, savemat_lineage
try:
    from cps.save import savehdf_snapshot, savehdf_lineage
except ImportError:
    pass

# Constants
from cps.misc import AgentQueue
ADD_AGENT = AgentQueue.ADD_AGENT
DELETE_AGENT = AgentQueue.DELETE_AGENT
del AgentQueue

# Release info
__author__   = '%s <%s>\n' % ('Nezar Abdennur', 'nabdennur@gmail.com')
__license__  = 'BSD'
__date__ = None
__version__ = None

