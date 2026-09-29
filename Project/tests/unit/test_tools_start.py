"""Every command-line tool shipped in Project/tools starts.

The release bundle ships Project/tools to every device, and the docs send
operators to these scripts. tools/valve_calibration_tool.py was advertised
as the headless calibration path for months while it could not even be
imported (it pointed at a module that no longer existed); nothing noticed
because nothing ran it. This runs each tool the way an operator does, as a
script with ``--help``, in a subprocess with the data directory pointed at
a scratch location, so a tool that cannot start fails here instead of on a
device.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[2]
TOOLS = sorted(p for p in (PROJECT / "tools").glob("*.py") if not p.name.startswith("_"))


def test_there_are_tools_to_check():
    assert TOOLS, "Project/tools is empty or moved; update this test"


@pytest.mark.parametrize("tool", TOOLS, ids=lambda p: p.name)
def test_tool_shows_its_help(tool, tmp_path):
    env = dict(
        os.environ,
        QT_QPA_PLATFORM="offscreen",
        RRR_DATA=str(tmp_path / "data"),  # never the developer's or a device's data
        PYTHONDONTWRITEBYTECODE="1",
    )
    result = subprocess.run(
        [sys.executable, str(tool), "--help"],
        cwd=str(PROJECT),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, (
        f"{tool.name} --help exited {result.returncode}\n{result.stderr[-2000:]}"
    )
    assert "usage" in result.stdout.lower(), f"{tool.name} printed no usage:\n{result.stdout}"
    assert not (tmp_path / "data").exists(), f"{tool.name} --help created a data directory"
