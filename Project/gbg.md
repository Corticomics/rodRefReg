Ideas for RRR
- yt channel with videos setup instructions step by step
- 



   wget -O setup_rrr.sh https://raw.githubusercontent.com/Corticomics/rodRefReg/main/setup_rrr.sh && chmod +x setup_rrr.sh && ./setup_rrr.sh


   Collecting PyQt5==5.15.4 (from -r installer/requirements.txt (line 2))
  Downloading PyQt5-5.15.4.tar.gz (3.3 MB)
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 3.3/3.3 MB 2.6 MB/s eta 0:00:00
  Installing build dependencies ... done
  Getting requirements to build wheel ... done
  Preparing metadata (pyproject.toml) ... error
  error: subprocess-exited-with-error
  
  × Preparing metadata (pyproject.toml) did not run successfully.
  │ exit code: 1
  ╰─> [26 lines of output]
      pyproject.toml: line 7: using '[tool.sip.metadata]' to specify the project metadata is deprecated and will be removed in SIP v7.0.0, use '[project]' instead
      Traceback (most recent call last):
        File "/home/rrrinstaller/rodent-refreshment-regulator/venv/lib/python3.11/site-packages/pip/_vendor/pyproject_hooks/_in_process/_in_process.py", line 389, in <module>
          main()
        File "/home/rrrinstaller/rodent-refreshment-regulator/venv/lib/python3.11/site-packages/pip/_vendor/pyproject_hooks/_in_process/_in_process.py", line 373, in main
          json_out["return_val"] = hook(**hook_input["kwargs"])
                                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        File "/home/rrrinstaller/rodent-refreshment-regulator/venv/lib/python3.11/site-packages/pip/_vendor/pyproject_hooks/_in_process/_in_process.py", line 178, in prepare_metadata_for_build_wheel
          whl_basename = backend.build_wheel(metadata_directory, config_settings)
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        File "/tmp/pip-build-env-ynv35irq/overlay/lib/python3.11/site-packages/sipbuild/api.py", line 28, in build_wheel
          project = AbstractProject.bootstrap('wheel',
                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        File "/tmp/pip-build-env-ynv35irq/overlay/lib/python3.11/site-packages/sipbuild/abstract_project.py", line 74, in bootstrap
          project.setup(pyproject, tool, tool_description)
        File "/tmp/pip-build-env-ynv35irq/overlay/lib/python3.11/site-packages/sipbuild/project.py", line 629, in setup
          self.apply_user_defaults(tool)
        File "/tmp/pip-install-wpmgtbb5/pyqt5_24d688bb739c434a9ed741e35bd00b50/project.py", line 63, in apply_user_defaults
          super().apply_user_defaults(tool)
        File "/tmp/pip-build-env-ynv35irq/overlay/lib/python3.11/site-packages/pyqtbuild/project.py", line 51, in apply_user_defaults
          super().apply_user_defaults(tool)
        File "/tmp/pip-build-env-ynv35irq/overlay/lib/python3.11/site-packages/sipbuild/project.py", line 243, in apply_user_defaults
          self.builder.apply_user_defaults(tool)
        File "/tmp/pip-build-env-ynv35irq/overlay/lib/python3.11/site-packages/pyqtbuild/builder.py", line 49, in apply_user_defaults
          raise PyProjectOptionException('qmake',
      sipbuild.pyproject.PyProjectOptionException
      [end of output]
  
  note: This error originates from a subprocess, and is likely not a problem with pip.
error: metadata-generation-failed
