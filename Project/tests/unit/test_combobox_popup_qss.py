"""Both themes use the non-scrollable combo popup (QA item #7).

With a stylesheet applied, Qt switches QComboBox to a scrollable popup whose
height is computed from the font row height rather than the styled
(min-height + padding) row height, so the last item is clipped behind a scroll
arrow. `combobox-popup: 0` reverts to the classic popup that fits all items.
Guard that the rule stays in both theme stylesheets. Pure file read — no Qt.
"""

from __future__ import annotations

from pathlib import Path

STYLE_DIR = Path(__file__).resolve().parents[2] / "ui" / "style"


def test_both_themes_use_fit_to_contents_combo_popup():
    for name in ("app-light.qss", "app-dark.qss"):
        text = (STYLE_DIR / name).read_text(encoding="utf-8")
        assert "combobox-popup: 0" in text, f"{name} is missing combobox-popup: 0"
