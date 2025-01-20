Running program with schedule: instant1, mode: Instant, window_start: 1737403027, window_end: 1737403033
Program Started
Starting instant cycle
Processing 3 deliveries
Processing delivery time: 2025-01-20 19:57:07.840000
Skipping past delivery time: 2025-01-20 19:57:07.840000
Processing delivery time: 2025-01-20 19:57:10.608000
Skipping past delivery time: 2025-01-20 19:57:10.608000
Processing delivery time: 2025-01-20 19:57:13.345000
Skipping past delivery time: 2025-01-20 19:57:13.345000
No future deliveries to schedule
[DEBUG] Starting cleanup process
[DEBUG] All relays deactivated
[DEBUG] Worker was already deleted or disconnected: wrapped C/C++ object of type RelayWorker has been deleted
[DEBUG] Cleanup completed. Program ready for the next job.
Running program with schedule: staggered mode test 3, mode: Staggered, window_start: 1737403103, window_end: 1737406693
Program Started
Starting staggered cycle
Traceback (most recent call last):
  File "/home/mouseuser/Documents/GitHub/rodRefReg/Project/gpio/relay_worker.py", line 58, in run_cycle
    self.run_staggered_cycle()
  File "/home/mouseuser/Documents/GitHub/rodRefReg/Project/gpio/relay_worker.py", line 137, in run_staggered_cycle
    for relay_unit_id, triggers_per_cycle in self.settings['num_triggers'].items():
                                             ~~~~~~~~~~~~~^^^^^^^^^^^^^^^^
KeyError: 'num_triggers'