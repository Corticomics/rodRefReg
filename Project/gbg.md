Error logging delivery: NOT NULL constraint failed: dispensing_history.schedule_id
Traceback (most recent call last):

  File "/home/mouseuser/Documents/GitHub/rodRefReg/Project/models/database_handler.py", line 1268, in log_delivery
    cursor.execute('''

sqlite3.IntegrityError: NOT NULL constraint failed: dispensing_history.schedule_id


mouseuser@raspberrypi:~/Documents/GitHub/rodRefReg/Project $ sudo python3 main.py
QStandardPaths: XDG_RUNTIME_DIR not set, defaulting to '/tmp/runtime-root'
Database error during table creation: duplicate column name: cycle_index
Traceback (most recent call last):
  File "/home/mouseuser/Documents/GitHub/rodRefReg/Project/models/database_handler.py", line 185, in create_tables
    cursor.execute('''
sqlite3.OperationalError: duplicate column name: cycle_index
Database error during table creation: duplicate column name: cycle_index
Traceback (most recent call last):
  File "/home/mouseuser/Documents/GitHub/rodRefReg/Project/models/database_handler.py", line 185, in create_tables
    cursor.execute('''
sqlite3.OperationalError: duplicate column name: cycle_index

Failed to pause schedule: 'RunStopSection' object has no attribute 'schedule_manager

Running program with schedule: test, mode: Staggered
Failed to run program: wrapped C/C++ object of type QThread has been deleted

Logged pump trigger: {'timestamp': '2025-01-29T17:36:59.914151', 'relay_info': 'Program error: wrapped C/C++ object of type QThread has been deleted'}
Error stopping program: wrapped C/C++ object of type QTimer has been deleted