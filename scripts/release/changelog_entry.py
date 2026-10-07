#!/usr/bin/env python3
"""Print the CHANGELOG.md entry for one version, for the GitHub Release notes.

The release workflow runs this for the tagged version and passes the output
to ``gh release create --notes-file``: the in-app Updates tab shows the
Release body, and nothing else tells an operator what to do before updating
(MAINTENANCE.md section 3a, step 4b). It exits 1 with a message when the
entry is missing, so the Release is not created with the wrong notes.

An entry starts at a line ``## <version>`` (anything may follow the version
after a space) and ends before the next ``## `` heading. A pre-release
``X.Y.Z-beta`` uses its own entry when there is one, else the ``X.Y.Z``
entry.

Usage: changelog_entry.py <version> [--changelog PATH]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHANGELOG = REPO_ROOT / "CHANGELOG.md"


def candidate_versions(version: str) -> list[str]:
    """The version itself, then the stable version a pre-release belongs to."""
    version = version.strip()
    if version.startswith("v"):
        version = version[1:]
    stable = re.sub(r"-.*$", "", version)
    return [version] if stable == version else [version, stable]


def find_entry(text: str, version: str) -> str | None:
    """The entry for ``version``: its heading line and body, or None."""
    lines = text.splitlines()
    for wanted in candidate_versions(version):
        heading = re.compile(r"^## " + re.escape(wanted) + r"(\s|$)")
        for index, line in enumerate(lines):
            if not heading.match(line):
                continue
            body = []
            for later in lines[index + 1 :]:
                if later.startswith("## "):
                    break
                body.append(later)
            while body and not body[-1].strip():
                body.pop()
            return "\n".join([line, *body]).strip() + "\n"
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("version", help="the version to look up, e.g. 1.21.0 or v1.21.0")
    parser.add_argument(
        "--changelog",
        type=Path,
        default=DEFAULT_CHANGELOG,
        help=f"the changelog to read (default: {DEFAULT_CHANGELOG})",
    )
    args = parser.parse_args(argv)
    try:
        text = args.changelog.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"cannot read {args.changelog}: {exc}", file=sys.stderr)
        return 2
    entry = find_entry(text, args.version)
    if entry is None:
        tried = " or ".join(f"'## {v}'" for v in candidate_versions(args.version))
        print(
            f"{args.changelog.name} has no entry for {args.version}: add a heading {tried} "
            "with the release notes (MAINTENANCE.md section 3a, step 4b).",
            file=sys.stderr,
        )
        return 1
    sys.stdout.write(entry)
    return 0


if __name__ == "__main__":
    sys.exit(main())
