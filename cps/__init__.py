"""
Copyright (C) 2012, Nezar Abdennur <nabdennur@gmail.com>

Permission to use, copy, modify, and/or distribute this software for any purpose
with or without fee is hereby granted, provided that the above copyright notice
and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS
OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER
TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF
THIS SOFTWARE.

Dynamical Systems Biology Laboratory
www.sysbiolab.uottawa.ca

"""
#!/usr/bin/env python

from cps.channel import AgentChannel, WorldChannel, RecordingChannel
from cps.state import Recorder
from cps.save import savemat_snapshot, savemat_lineage, savehdf_snapshot, savehdf_lineage
from cps.simulator import FEMethodSimulator, AsyncMethodSimulator
from cps.model import Model

from cps.entity import AgentQueue
ADD_AGENT = AgentQueue.ADD_AGENT
DELETE_AGENT = AgentQueue.DELETE_AGENT
del AgentQueue

__author__   = '%s <%s>\n' % ('Nezar Abdennur', 'nabdennur@gmail.com')
__license__  = 'ISC'
__date__ = None
__version__ = None

