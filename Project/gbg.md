Running program with schedule: fr2, mode: Instant, window_start: 1733871475, window_end: 1733871535
Program Started
Waiting 79 seconds until window start
Waiting 1 seconds until window start
Traceback (most recent call last):
  File "/home/conelab/Documents/GitHub/new_rrr/RRR/Project/gpio/relay_worker.py", line 97, in run_staggered_cycle
    for relay_unit_id, triggers in self.settings['num_triggers'].items():
                                   ~~~~~~~~~~~~~^^^^^^^^^^^^^^^^
KeyError: 'num_triggers'
