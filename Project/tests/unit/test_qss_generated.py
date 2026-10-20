"""The theme stylesheets are generated from one template and one token table.

app-light.qss and app-dark.qss are committed, but written by
Project/ui/style/build_qss.py from app.qss.tmpl and tokens.py. These tests fail when a
committed stylesheet differs from the render (a hand edit, or a template or token change
that was not regenerated), when the template names a role tokens.py lacks or holds a raw
colour, when a role is unused, and when the two themes stop sharing their rules.
Pure file reads and string work, no Qt.
"""

from __future__ import annotations

import importlib.util
import re
import shutil
from pathlib import Path

import pytest

STYLE_DIR = Path(__file__).resolve().parents[2] / "ui" / "style"


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, STYLE_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build_qss = _load("rrr_build_qss_under_test", "build_qss.py")
tokens = _load("rrr_tokens_under_test", "tokens.py")

PLACEHOLDER = re.compile(r"\$\{([^}]*)\}")
COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
RAW_COLOUR = re.compile(
    r"(?<![\w#&])#[0-9A-Fa-f]{3,8}\b|\brgba?\s*\("
    r"|\b(?:white|black|red|green|blue|gray|grey|yellow|orange|cyan|magenta)\b",
    re.IGNORECASE,
)

# Declarations one theme has and the other lacks. Today the dark theme sets the text
# colour on these surfaces and the light theme inherits it; every other declaration, and
# every rule, is in both themes. A new entry here is a decision, not a side effect.
DARK_ONLY = {
    ("QTableView, QTableWidget", "color"),
    ("QGroupBox", "color"),
    ("QListWidget", "color"),
    ("QGroupBox QLabel", "color"),
    ("QTextEdit#WizardLog", "color"),
    ("QMenuBar::item", "color"),
    ("QMenu::item", "color"),
    ("QPushButton#WizardBackButton:hover", "color"),
    ("QTreeWidget#HelpTree", "color"),
    ("QTextBrowser#HelpContent", "color"),
}


def _template():
    return build_qss.TEMPLATE.read_text(encoding="utf-8")


def _placeholders(theme):
    """Placeholder names in the lines `theme` keeps (template comments excluded)."""
    return {
        name
        for _, line in build_qss.theme_lines(_template(), theme)
        for name in PLACEHOLDER.findall(line)
    }


def _rules(qss):
    """[(selector, [property, ...])] in file order, comments removed."""
    rules = []
    for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", COMMENT.sub("", qss)):
        props = [d.split(":", 1)[0].strip() for d in body.split(";") if ":" in d]
        rules.append((" ".join(selector.split()), props))
    return rules


@pytest.mark.parametrize("theme", build_qss.THEMES)
def test_the_committed_stylesheet_is_the_render(theme):
    committed = build_qss.OUTPUTS[theme].read_bytes().decode("utf-8")
    assert committed.startswith(build_qss.HEADER)
    assert committed == build_qss.render(theme), (
        f"{build_qss.OUTPUTS[theme].name} differs from app.qss.tmpl + tokens.py: edit those, "
        "then run python3 Project/ui/style/build_qss.py and commit the result"
    )


def test_check_mode_reports_a_stale_stylesheet_and_a_build_fixes_it(tmp_path, monkeypatch):
    outputs = {}
    for theme, path in build_qss.OUTPUTS.items():
        outputs[theme] = tmp_path / path.name
        shutil.copyfile(path, outputs[theme])
    monkeypatch.setattr(build_qss, "OUTPUTS", outputs)
    assert build_qss.main(["--check"]) == 0

    edited = outputs["dark"].read_text(encoding="utf-8").replace("#1E2530", "#1E2531", 1)
    outputs["dark"].write_text(edited, encoding="utf-8")
    assert build_qss.main(["--check"]) == 1
    assert outputs["dark"].read_text(encoding="utf-8") == edited, "--check writes nothing"

    assert build_qss.main([]) == 0
    assert build_qss.main(["--check"]) == 0
    for theme in build_qss.THEMES:
        assert outputs[theme].read_bytes() == build_qss.OUTPUTS[theme].read_bytes()
        assert outputs[theme].read_bytes() == build_qss.render(theme).encode("utf-8")


def test_every_placeholder_names_a_token():
    for theme in build_qss.THEMES:
        unknown = _placeholders(theme) - set(tokens.TOKENS)
        assert not unknown, f"app.qss.tmpl uses roles tokens.py lacks: {sorted(unknown)}"
        lines = build_qss.theme_lines(_template(), theme)
        unbraced = [number for number, line in lines if re.search(r"\$(?!\{)", line)]
        assert not unbraced, f"write each placeholder as ${{role}}: app.qss.tmpl lines {unbraced}"


def test_every_token_is_used():
    used = set().union(*(_placeholders(theme) for theme in build_qss.THEMES))
    unused = set(tokens.TOKENS) - used
    assert not unused, f"tokens.py roles the template never uses: {sorted(unused)}"


@pytest.mark.parametrize(
    ("template", "message"),
    [
        ("a { color: ${no.such.role}; }\n", r"line 1: unknown token \$\{no\.such\.role\}"),
        ("a {\n    color: $(bg.page);\n}\n", "line 2: malformed placeholder"),
        ("@light\na { }\n", "line 1: the @light block has no @end"),
        ("a { }\n@end\n", "line 2: @end without @light or @dark"),
        ("@dark\n@dark\n@end\n", "line 2: @dark inside a @dark block"),
        ("@lite\na { }\n", "line 1: unknown directive '@lite'"),
    ],
)
def test_a_broken_template_stops_the_build(template, message):
    with pytest.raises(build_qss.TemplateError, match=message):
        build_qss.render("light", template_text=template, values={"bg.page": "#FFFFFF"})


def test_theme_blocks_and_template_comments():
    template = (
        "@# a template comment, never written out\n"
        "a {\n"
        "    background: ${bg.page};\n"
        "@light\n"
        "    /* light only */\n"
        "@dark\n"
        "    color: ${text.primary};\n"
        "@end\n"
        "}\n"
    )
    values = {"bg.page": "#111111", "text.primary": "#222222"}
    light = build_qss.render("light", template_text=template, values=values)
    dark = build_qss.render("dark", template_text=template, values=values)
    assert light == build_qss.HEADER + "a {\n    background: #111111;\n    /* light only */\n}\n"
    assert dark == build_qss.HEADER + "a {\n    background: #111111;\n    color: #222222;\n}\n"


def test_the_template_holds_no_raw_colour():
    for theme in build_qss.THEMES:
        text = "\n".join(line for _, line in build_qss.theme_lines(_template(), theme))
        hits = RAW_COLOUR.findall(COMMENT.sub("", text))
        assert not hits, f"raw colours in app.qss.tmpl (use a ${{role}}): {sorted(set(hits))}"


def test_tokens_are_colours_named_by_role():
    for name, pair in tokens.TOKENS.items():
        assert re.fullmatch(build_qss.QssTemplate.idpattern, name), name
        assert isinstance(pair, tuple) and len(pair) == len(tokens.THEMES), name
        for colour in pair:
            assert re.fullmatch(r"#[0-9A-F]{6}|white", colour), f"{name}: {colour!r}"


def test_value_gives_each_themes_colour():
    assert tokens.THEMES == build_qss.THEMES
    for name, (light, dark) in tokens.TOKENS.items():
        assert tokens.value(name, "light") == light
        assert tokens.value(name, "dark") == dark
    with pytest.raises(KeyError):
        tokens.value("no.such.role", "light")
    with pytest.raises(ValueError, match="unknown theme"):
        tokens.value("bg.page", "sepia")


def test_both_themes_share_every_rule():
    light, dark = (_rules(build_qss.render(theme)) for theme in build_qss.THEMES)
    assert [s for s, _ in light] == [s for s, _ in dark], "the themes' rules differ"
    pairs = list(zip(light, dark))
    theme_only = {"light": set(), "dark": set()}
    for (selector, light_props), (_, dark_props) in pairs:
        theme_only["light"] |= {(selector, p) for p in light_props if p not in dark_props}
        theme_only["dark"] |= {(selector, p) for p in dark_props if p not in light_props}
    expected = {"light": set(), "dark": DARK_ONLY}
    new = {t: sorted(theme_only[t] - expected[t]) for t in expected}
    gone = {t: sorted(expected[t] - theme_only[t]) for t in expected}
    assert not any(new.values()) and not any(gone.values()), (
        f"declarations only one theme has: new {new}, no longer theme-only {gone} "
        "(share them, or update DARK_ONLY on purpose)"
    )
    for (selector, light_props), (_, dark_props) in pairs:
        shared = [p for p in dark_props if (selector, p) not in DARK_ONLY]
        assert shared == light_props, f"{selector}: the themes order their declarations apart"
