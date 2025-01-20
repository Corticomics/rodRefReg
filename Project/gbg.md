mouseuser@raspberrypi:~/Documents/GitHub/rodRefReg/Project $ python3 test_relay_connection.py 
Traceback (most recent call last):
  File "/usr/local/lib/python3.11/dist-packages/SM16relind-1.0.2-py3.11.egg/SM16relind/__init__.py", line 24, in __init__
  File "/usr/lib/python3/dist-packages/smbus2/smbus2.py", line 474, in read_word_data
    ioctl(self.fd, I2C_SMBUS, msg)
TimeoutError: [Errno 110] Connection timed out

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "/home/mouseuser/Documents/GitHub/rodRefReg/Project/test_relay_connection.py", line 3, in <module>
    rel = SM16relind.SM16relind(0)
          ^^^^^^^^^^^^^^^^^^^^^^^^
  File "/usr/local/lib/python3.11/dist-packages/SM16relind-1.0.2-py3.11.egg/SM16relind/__init__.py", line 31, in __init__
Exception: Fail to init the card with exception [Errno 110] Connection timed out
mouseuser@raspberrypi:~/Documents/GitHub/rodRefReg/Project $ 
