"""SolenoidFlowStrategy defaults to pulse mode (QA item #14a).

SystemController force-enforces use_pulse_delivery=True on every settings load,
so pulse is the canonical delivery mode. This guards the strategy's own
fallback so it agrees with that intent (pulse unless explicitly disabled) for
any path that builds the strategy directly. Validated on-device (Pi).
"""

from __future__ import annotations

from strategies.solenoid_flow_strategy import SolenoidFlowStrategy


def _make(settings):
    return SolenoidFlowStrategy(
        solenoid_controller=object(),
        flow_sensor=None,
        calibration_store=None,
        settings=settings,
    )


def test_defaults_to_pulse_when_setting_absent():
    assert _make({})._use_pulse_mode is True


def test_continuous_only_when_explicitly_disabled():
    assert _make({"use_pulse_delivery": False})._use_pulse_mode is False


def test_pulse_when_explicitly_enabled():
    assert _make({"use_pulse_delivery": True})._use_pulse_mode is True
