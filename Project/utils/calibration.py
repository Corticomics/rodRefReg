from __future__ import annotations

import json
import os
from typing import Dict, Optional


class CalibrationStore:
    """Persist and load sensor calibration factors.

    Data format (JSON):
    {
      "sensors": {
        "slf3s-addr-0x08": {"zero_offset_ml_min": 0.12, "span_scale": 1.003}
      }
    }
    """

    def __init__(self, path: str = "settings/calibration.json") -> None:
        self._path = path
        self._data = {"sensors": {}}  # type: Dict[str, Dict[str, float]]
        self._load()

    def _load(self) -> None:
        try:
            if os.path.exists(self._path):
                with open(self._path, "r") as f:
                    self._data = json.load(f)
        except Exception:
            self._data = {"sensors": {}}

    def save(self) -> None:
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w") as f:
            json.dump(self._data, f, indent=2)

    def get(self, sensor_key: str) -> Dict[str, float]:
        return self._data.get("sensors", {}).get(sensor_key, {}).copy()

    def set(self, sensor_key: str, *, zero_offset_ml_min: float, span_scale: float) -> None:
        self._data.setdefault("sensors", {})[sensor_key] = {
            "zero_offset_ml_min": float(zero_offset_ml_min),
            "span_scale": float(span_scale),
        }
        self.save()
