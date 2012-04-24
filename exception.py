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
class SimulationError(Exception):
    """
    Base class for exceptions in this module.

    """
    pass


class SchedulingError(SimulationError):
    """
    Raise if an event was scheduled to occur at a time preceding the entity's
    current clock time.

    """
    def __init__(self, entity, channel, clock_time, sched_time):
        self.entity = entity
        self.channel = channel
        self.clock_time = clock_time
        self.sched_time = sched_time

    def __str__(self):
        return repr(self.channel) + ' ' + \
               'attempted to schedule an event at t=' + str(self.sched_time) + ', ' + \
               'but the agent\'s clock is currently at t=' + str(self.clock_time) + '.'


def main():
    pass

if __name__ == '__main__':
    main()
