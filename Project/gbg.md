Ideas for RRR
- yt channel with videos setup instructions step by step
- 



   wget -O setup_rrr.sh https://raw.githubusercontent.com/Corticomics/rodRefReg/main/setup_rrr.sh && chmod +x setup_rrr.sh && ./setup_rrr.sh

Building wheels for collected packages: RPi.GPIO
  Building wheel for RPi.GPIO (pyproject.toml) ... error
  error: subprocess-exited-with-error
  
  × Building wheel for RPi.GPIO (pyproject.toml) did not run successfully.
  │ exit code: 1
  ╰─> [91 lines of output]
      /tmp/pip-build-env-4s7_8kkp/overlay/lib/python3.11/site-packages/setuptools/dist.py:759: SetuptoolsDeprecationWarning: License classifiers are deprecated.
      !!
      
              ********************************************************************************
              Please consider removing the following classifiers in favor of a SPDX license expression:
      
              License :: OSI Approved :: MIT License
      
              See https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#license for details.
              ********************************************************************************
      
      !!
        self._finalize_license_expression()
      source/c_gpio.c: In function ‘setup’:
      source/c_gpio.c:130:9: warning: cast from pointer to integer of different size [-Wpointer-to-int-cast]
        130 |     if ((uint32_t)gpio_mem % PAGE_SIZE)
            |         ^
      source/c_gpio.c:131:34: warning: cast from pointer to integer of different size [-Wpointer-to-int-cast]
        131 |         gpio_mem += PAGE_SIZE - ((uint32_t)gpio_mem % PAGE_SIZE);
            |                                  ^
      source/cpuinfo.c: In function ‘get_rpi_info’:
      source/cpuinfo.c:139:28: warning: format ‘%llx’ expects argument of type ‘long long unsigned int *’, but argument 3 has type ‘uint64_t *’ {aka ‘long unsigned int *’} [-Wformat=]
        139 |       sscanf(revision, "%llx", &rev);
            |                         ~~~^   ~~~~
            |                            |   |
            |                            |   uint64_t * {aka long unsigned int *}
            |                            long long unsigned int *
            |                         %lx
      source/py_gpio.c: In function ‘PyInit__GPIO’:
      source/py_gpio.c:1046:4: warning: ‘PyEval_ThreadsInitialized’ is deprecated [-Wdeprecated-declarations]
       1046 |    if (!PyEval_ThreadsInitialized())
            |    ^~
      In file included from /usr/include/python3.11/Python.h:95,
                       from source/py_gpio.c:23:
      /usr/include/python3.11/ceval.h:131:36: note: declared here
        131 | Py_DEPRECATED(3.9) PyAPI_FUNC(int) PyEval_ThreadsInitialized(void);
            |                                    ^~~~~~~~~~~~~~~~~~~~~~~~~
      source/py_gpio.c:1047:7: warning: ‘PyEval_InitThreads’ is deprecated [-Wdeprecated-declarations]
       1047 |       PyEval_InitThreads();
            |       ^~~~~~~~~~~~~~~~~~
      /usr/include/python3.11/ceval.h:132:37: note: declared here
        132 | Py_DEPRECATED(3.9) PyAPI_FUNC(void) PyEval_InitThreads(void);
            |                                     ^~~~~~~~~~~~~~~~~~
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/constants.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:41: multiple definition of `module_setup'; build/temp.linux-aarch64-cpython-311/source/common.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:41: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/constants.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:40: multiple definition of `setup_error'; build/temp.linux-aarch64-cpython-311/source/common.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:40: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/constants.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:39: multiple definition of `rpiinfo'; build/temp.linux-aarch64-cpython-311/source/common.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:39: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/constants.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:38: multiple definition of `gpio_direction'; build/temp.linux-aarch64-cpython-311/source/common.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:38: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/constants.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:37: multiple definition of `pin_to_gpio'; build/temp.linux-aarch64-cpython-311/source/common.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:37: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/constants.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:36: multiple definition of `pin_to_gpio_rev3'; build/temp.linux-aarch64-cpython-311/source/common.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:36: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/constants.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:35: multiple definition of `pin_to_gpio_rev2'; build/temp.linux-aarch64-cpython-311/source/common.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:35: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/constants.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:34: multiple definition of `pin_to_gpio_rev1'; build/temp.linux-aarch64-cpython-311/source/common.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:34: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/constants.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:33: multiple definition of `gpio_mode'; build/temp.linux-aarch64-cpython-311/source/common.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:33: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_gpio.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:40: multiple definition of `setup_error'; build/temp.linux-aarch64-cpython-311/source/common.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:40: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_gpio.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:33: multiple definition of `gpio_mode'; build/temp.linux-aarch64-cpython-311/source/common.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:33: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_gpio.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:39: multiple definition of `rpiinfo'; build/temp.linux-aarch64-cpython-311/source/common.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:39: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_gpio.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:41: multiple definition of `module_setup'; build/temp.linux-aarch64-cpython-311/source/common.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:41: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_gpio.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:38: multiple definition of `gpio_direction'; build/temp.linux-aarch64-cpython-311/source/common.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:38: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_gpio.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:37: multiple definition of `pin_to_gpio'; build/temp.linux-aarch64-cpython-311/source/common.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:37: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_gpio.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:35: multiple definition of `pin_to_gpio_rev2'; build/temp.linux-aarch64-cpython-311/source/common.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:35: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_gpio.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:36: multiple definition of `pin_to_gpio_rev3'; build/temp.linux-aarch64-cpython-311/source/common.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:36: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_gpio.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:34: multiple definition of `pin_to_gpio_rev1'; build/temp.linux-aarch64-cpython-311/source/common.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:34: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_gpio.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/constants.h:42: multiple definition of `both_edge'; build/temp.linux-aarch64-cpython-311/source/constants.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/constants.h:42: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_gpio.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/constants.h:41: multiple definition of `falling_edge'; build/temp.linux-aarch64-cpython-311/source/constants.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/constants.h:41: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_gpio.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/constants.h:40: multiple definition of `rising_edge'; build/temp.linux-aarch64-cpython-311/source/constants.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/constants.h:40: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_gpio.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/constants.h:39: multiple definition of `pud_down'; build/temp.linux-aarch64-cpython-311/source/constants.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/constants.h:39: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_gpio.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/constants.h:38: multiple definition of `pud_up'; build/temp.linux-aarch64-cpython-311/source/constants.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/constants.h:38: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_gpio.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/constants.h:37: multiple definition of `pud_off'; build/temp.linux-aarch64-cpython-311/source/constants.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/constants.h:37: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_gpio.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/constants.h:36: multiple definition of `bcm'; build/temp.linux-aarch64-cpython-311/source/constants.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/constants.h:36: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_gpio.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/constants.h:35: multiple definition of `board'; build/temp.linux-aarch64-cpython-311/source/constants.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/constants.h:35: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_gpio.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/constants.h:34: multiple definition of `unknown'; build/temp.linux-aarch64-cpython-311/source/constants.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/constants.h:34: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_gpio.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/constants.h:33: multiple definition of `spi'; build/temp.linux-aarch64-cpython-311/source/constants.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/constants.h:33: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_gpio.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/constants.h:32: multiple definition of `i2c'; build/temp.linux-aarch64-cpython-311/source/constants.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/constants.h:32: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_gpio.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/constants.h:31: multiple definition of `serial'; build/temp.linux-aarch64-cpython-311/source/constants.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/constants.h:31: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_gpio.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/constants.h:30: multiple definition of `pwm'; build/temp.linux-aarch64-cpython-311/source/constants.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/constants.h:30: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_gpio.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/constants.h:29: multiple definition of `output'; build/temp.linux-aarch64-cpython-311/source/constants.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/constants.h:29: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_gpio.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/constants.h:28: multiple definition of `input'; build/temp.linux-aarch64-cpython-311/source/constants.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/constants.h:28: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_gpio.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/constants.h:27: multiple definition of `low'; build/temp.linux-aarch64-cpython-311/source/constants.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/constants.h:27: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_gpio.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/constants.h:26: multiple definition of `high'; build/temp.linux-aarch64-cpython-311/source/constants.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/constants.h:26: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_pwm.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:38: multiple definition of `gpio_direction'; build/temp.linux-aarch64-cpython-311/source/common.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:38: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_pwm.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/py_pwm.h:23: multiple definition of `PWMType'; build/temp.linux-aarch64-cpython-311/source/py_gpio.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/py_pwm.h:23: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_pwm.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:41: multiple definition of `module_setup'; build/temp.linux-aarch64-cpython-311/source/common.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:41: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_pwm.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:40: multiple definition of `setup_error'; build/temp.linux-aarch64-cpython-311/source/common.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:40: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_pwm.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:39: multiple definition of `rpiinfo'; build/temp.linux-aarch64-cpython-311/source/common.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:39: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_pwm.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:37: multiple definition of `pin_to_gpio'; build/temp.linux-aarch64-cpython-311/source/common.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:37: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_pwm.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:36: multiple definition of `pin_to_gpio_rev3'; build/temp.linux-aarch64-cpython-311/source/common.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:36: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_pwm.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:35: multiple definition of `pin_to_gpio_rev2'; build/temp.linux-aarch64-cpython-311/source/common.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:35: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_pwm.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:34: multiple definition of `pin_to_gpio_rev1'; build/temp.linux-aarch64-cpython-311/source/common.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:34: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/py_pwm.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:33: multiple definition of `gpio_mode'; build/temp.linux-aarch64-cpython-311/source/common.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/common.h:33: first defined here
      /usr/bin/ld: build/temp.linux-aarch64-cpython-311/source/soft_pwm.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/soft_pwm.c:28: multiple definition of `threads'; build/temp.linux-aarch64-cpython-311/source/event_gpio.o:/tmp/pip-install-6l7cmiux/rpi-gpio_e136dd1b9ba04e1bb511f44b1f3fb7bd/source/event_gpio.c:60: first defined here
      collect2: error: ld returned 1 exit status
      error: command '/usr/bin/aarch64-linux-gnu-gcc' failed with exit code 1
      [end of output]
  
  note: This error originates from a subprocess, and is likely not a problem with pip.
  ERROR: Failed building wheel for RPi.GPIO
Failed to build RPi.GPIO
ERROR: Failed to build installable wheels for some pyproject.toml based projects (RPi.GPIO)
=== Verifying slack_sdk installation ===
slack_sdk is installed correctly.
=== Verifying PyQt5 is accessible ===
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'PyQt5'
Warning: PyQt5 test failed. Installing system site packages...
Retesting PyQt5 access...
Traceback (most recent call last):
  File "<string>", line 1, in <module>
AttributeError: module 'PyQt5' has no attribute 'QtCore'
PyQt5 still not accessible. Please install manually after setup.
