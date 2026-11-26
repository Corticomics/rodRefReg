"""No tracked file holds a credential.

Once a commit is pushed, a credential in it stays in the history: deleting the file later
does not take it back, only rotating the credential does. This test fails the suite before
the commit is merged.

It checks the files git tracks (``git ls-files``). Where git cannot list them, it checks
every file under the repository root instead, leaving out the directories .gitignore keeps
out of git (.git, __pycache__, venvs, build, dist, vendor): in a release bundle, which has
no .git, and in CI's Bookworm container, where the checkout belongs to another user than
the one running the tests and git refuses it ("dubious ownership").

1. No tracked file sits where credentials or operator data live: Claude Code's settings
   (.claude/settings*.json, which record the commands an agent may run, passwords
   included), secrets.json, a SQLite database, Project/settings/settings.json, .env, a .pem
   or .key file, or an SSH key (id_rsa*, id_ed25519*, id_ecdsa*, id_dsa*).
2. No tracked text file holds a credential of a real shape: a Slack token, app token or
   webhook URL, a Brevo API or SMTP key, a GitHub token, an AWS access key id, a PEM
   private-key block, or a password written into a command (after ``sshpass -p``, in a
   ``SUDO_PWD`` or ``SSHPASS`` variable, or echoed into ``sudo -S``). A placeholder (a
   $variable, a command substitution, <password>) is not a password.

A failure names the file, the line and the kind, never the value, so the test's output
does not spread a credential further. The patterns match real shapes only, so a fixture
such as "xoxb-test" passes. A file that must hold something of a real shape goes in
ALLOWED, with the reason.

The samples the self-tests use are put together from fragments at run time, so this file
holds no literal that matches; it leaves itself out of the scan all the same.
"""

from __future__ import annotations

import fnmatch
import functools
import os
import re
import subprocess
from pathlib import Path, PurePosixPath

import pytest

ROOT = Path(__file__).resolve().parents[3]
THIS_FILE = Path(__file__).resolve().relative_to(ROOT).as_posix()

# {path relative to the root: (kind, why what it holds is not a credential)}. Nothing
# needs an entry today.
ALLOWED: dict[str, tuple[str, str]] = {}

# --- 1. Paths --------------------------------------------------------------------------

SSH_KEY_NAMES = ("id_rsa*", "id_ed25519*", "id_ecdsa*", "id_dsa*")


def banned_path_kind(relative):
    """The kind of credential file a path relative to the root names, or None."""
    path = PurePosixPath(relative)
    name = path.name.lower()
    if path.parent.name == ".claude" and fnmatch.fnmatchcase(name, "settings*.json"):
        return "Claude Code settings file"
    if name == "secrets.json":
        return "secrets file"
    if fnmatch.fnmatchcase(name, "*.db") or fnmatch.fnmatchcase(name, "*.sqlite*"):
        return "SQLite database"
    if relative == "Project/settings/settings.json":
        return "device settings file"
    if name == ".env":
        return "environment file"
    if fnmatch.fnmatchcase(name, "*.pem") or fnmatch.fnmatchcase(name, "*.key"):
        return "PEM or key file"
    if any(fnmatch.fnmatchcase(name, pattern) for pattern in SSH_KEY_NAMES):
        return "SSH key file"
    return None


# --- 2. Contents -----------------------------------------------------------------------

# Credentials of a real shape: (kind, pattern).
SHAPES = (
    ("Slack token", re.compile(r"\bxox[abposr]-(?:[0-9]+-)?[0-9]{8,}-[0-9A-Za-z-]{8,}")),
    (
        "Slack app token",
        re.compile(r"\bxapp-[0-9]+-[0-9A-Za-z]{6,}-[0-9]{6,}-[0-9A-Za-z]{16,}"),
    ),
    (
        "Slack webhook URL",
        re.compile(
            r"hooks\.slack\.com/(?:services|workflows|triggers)/"
            r"T[0-9A-Z]{6,}/[0-9A-Za-z]{6,}/[0-9A-Za-z/]{16,}"
        ),
    ),
    ("Brevo key", re.compile(r"\bx(?:keysib|smtpsib)-[0-9a-f]{64}-[0-9A-Za-z]{16}")),
    (
        "GitHub token",
        re.compile(r"\b(?:gh[pousr]_[0-9A-Za-z]{36,}|github_pat_[0-9A-Za-z_]{80,})"),
    ),
    ("AWS access key id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("private key block", re.compile(r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY(?: BLOCK)?-----")),
)

# What follows a command's password option: an optional quote (or a JSON-escaped one),
# then the value up to a space, a quote or shell punctuation. _is_literal decides.
_VALUE = r"""(?P<value>\\?["']?[^\s"'\\`;&|(),]*)"""

# A password written into a command: (kind, pattern with a "value" group).
COMMANDS = (
    (
        "password after sshpass -p",
        # sshpass's other options (-f file, -d fd, -P prompt, -e, -v) may come first
        re.compile(r"\bsshpass(?:[ \t]+-(?:[fdP][ \t]*\S+|[evhV]+))*[ \t]+-p[ \t]*" + _VALUE),
    ),
    ("password in SUDO_PWD", re.compile(r"\bSUDO_PWD(?P<spaces>[ \t]*=[ \t]*)" + _VALUE)),
    ("password in SSHPASS", re.compile(r"\bSSHPASS(?P<spaces>[ \t]*=[ \t]*)" + _VALUE)),
    (
        "password echoed into sudo -S",
        # echo's output piped straight into sudo, whose options (one may take an
        # argument, as -u root does) include -S
        re.compile(
            r"\becho[ \t]+(?:-[neE]+[ \t]+)*" + _VALUE + r"[^|\n]*\|[ \t]*sudo[ \t]+"
            r"(?:-\S+[ \t]+(?:[^-\s]\S*[ \t]+)?)*?-[A-Za-z]*S\b"
        ),
    ),
)

# How a placeholder starts: $PW, $(cat ~/.pw), <password>, {password}, %s, [password], ***
_PLACEHOLDER_START = ("$", "<", "{", "%", "[", "*", "\u2026")
_QUOTED = ('"', "'", '\\"', "\\'")


def _is_literal(value):
    """True when a command's password value is written out, not a placeholder."""
    core = re.sub(r"""^\\?["']""", "", value)
    if not core or core.startswith(_PLACEHOLDER_START):
        return False
    return not set(core) <= set("xX*.\u2026")  # xxx, ***, ...


def _line(text, offset):
    return text.count("\n", 0, offset) + 1


def hits_in(text):
    """[(line, kind)] for every credential in a text, sorted."""
    hits = set()
    for kind, pattern in SHAPES:
        hits.update((_line(text, match.start()), kind) for match in pattern.finditer(text))
    for kind, pattern in COMMANDS:
        for match in pattern.finditer(text):
            value = match.group("value")
            if "spaces" in pattern.groupindex and match.group("spaces") != "=":
                # SUDO_PWD = ... with spaces is a Python or YAML assignment: only a quoted
                # string is a written-out password (os.environ[...] is not)
                if not value.startswith(_QUOTED):
                    continue
            if _is_literal(value):
                hits.add((_line(text, match.start()), kind))
    return sorted(hits)


# --- Which files -----------------------------------------------------------------------

# Directories .gitignore keeps out of git: by name at any depth, and from the root
SKIPPED_DIRS = frozenset(
    {
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        ".tox",
        ".venv",
        "venv",
        "node_modules",
        "build",
        "dist",
        "vendor",
    }
)
SKIPPED_FROM_ROOT = frozenset({".claude/worktrees", "Project/rodrefreg"})
# Read as bytes, these hold no text worth scanning
BINARY_SUFFIXES = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".ico",
        ".pdf",
        ".woff",
        ".woff2",
        ".ttf",
        ".otf",
        ".zip",
        ".gz",
        ".tgz",
        ".xz",
        ".bz2",
        ".pyc",
        ".rrrupdate",
    }
)
# A git hook's environment would point git at another repository or index
_GIT_LOCATION_VARS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR")


def _join(directory, name):
    return name if directory == "." else f"{directory}/{name}"


def _walk(root):
    """Every file under root, relative to it, outside the skipped directories."""
    found = []
    for directory, dirnames, filenames in os.walk(root):
        relative = Path(directory).relative_to(root).as_posix()
        dirnames[:] = sorted(
            name
            for name in dirnames
            if name not in SKIPPED_DIRS and _join(relative, name) not in SKIPPED_FROM_ROOT
        )
        found += [_join(relative, name) for name in sorted(filenames) if name != ".git"]
    return found


def list_files(root):
    """(files to check, relative to root; how they were listed)."""
    if not (root / ".git").exists():
        reason = "there is no .git (a release bundle)"
    else:
        env = {key: value for key, value in os.environ.items() if key not in _GIT_LOCATION_VARS}
        try:
            done = subprocess.run(
                ["git", "-C", str(root), "ls-files", "-z"],
                capture_output=True,
                env=env,
                timeout=60,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            reason = f"git could not run ({type(exc).__name__})"
        else:
            names = [os.fsdecode(name) for name in done.stdout.split(b"\0") if name]
            if done.returncode == 0 and names:
                return names, "the files git tracks"
            said = done.stderr.decode("utf-8", errors="replace").strip().splitlines()
            if done.returncode == 0:
                reason = "git ls-files listed nothing"
            else:
                reason = f"git ls-files failed (exit {done.returncode}: {said[0] if said else ''})"
    return _walk(root), f"every file under the root, because {reason}"


@functools.lru_cache(maxsize=None)
def _tree():
    return list_files(ROOT)


def _text(path):
    """A file's text, or None for a binary file, a link or anything not a file."""
    if path.is_symlink() or not path.is_file() or path.suffix.lower() in BINARY_SUFFIXES:
        return None
    data = path.read_bytes()
    if b"\0" in data[:8192]:
        return None
    return data.decode("utf-8", errors="replace")


def _allowed(relative, kind):
    entry = ALLOWED.get(relative)
    return entry is not None and entry[0] == kind


def findings(root, files):
    """["path:line: kind"] for every credential the files hold, never the value.

    The text stays inside this function, so no traceback or --showlocals output of the
    test that asserts on the result can show it.
    """
    found = []
    for relative in files:
        if relative == THIS_FILE:
            continue
        text = _text(root / relative)
        if text is None:
            continue
        found += [
            f"{relative}:{line}: {kind}"
            for line, kind in hits_in(text)
            if not _allowed(relative, kind)
        ]
    return found


def report(found, listed):
    return (
        f"Credentials in the tree ({len(found)}; checked {listed}). Values are not shown. "
        "Take each one out; if it was ever pushed, rotate it as well (revoke the token or "
        "key, change the password): the history keeps it. Something that only looks like "
        "a credential goes in ALLOWED in this test, with the reason. See CONTRIBUTING.md, "
        "Credentials.\n" + "\n".join(found)
    )


# --- The tree --------------------------------------------------------------------------


def test_the_scan_sees_the_tree():
    files, listed = _tree()
    for expected in ("Project/version.py", "Project/tests/unit/conftest.py"):
        assert expected in files, f"{expected} is not among {listed}: the scan sees nothing"


def test_no_tracked_file_sits_where_credentials_live():
    files, listed = _tree()
    found = []
    for relative in files:
        kind = banned_path_kind(relative)
        if kind is not None and not _allowed(relative, kind):
            found.append(f"{relative}: {kind}")
    assert not found, (
        f"Files that hold credentials or operator data are tracked (checked {listed}). "
        "Untrack each with git rm --cached and keep it ignored; if it held a credential "
        "and was ever pushed, rotate it. See CONTRIBUTING.md, Credentials.\n" + "\n".join(found)
    )


def test_no_tracked_file_holds_a_credential():
    files, listed = _tree()
    found = findings(ROOT, files)
    assert not found, report(found, listed)


def _kinds_in(path):
    """The kinds of credential a file holds (its text stays in here, as in findings)."""
    text = _text(path)
    return set() if text is None else {kind for _, kind in hits_in(text)}


def test_every_allowed_entry_is_still_needed():
    files, _listed = _tree()
    stale = []
    for relative, (kind, reason) in sorted(ALLOWED.items()):
        assert reason.strip(), f"ALLOWED[{relative!r}] gives no reason"
        if relative not in files:
            stale.append(f"{relative}: no such file is checked")
        elif banned_path_kind(relative) != kind and kind not in _kinds_in(ROOT / relative):
            stale.append(f"{relative}: holds no {kind}")
    assert not stale, "Delete these entries from ALLOWED:\n" + "\n".join(stale)


# --- Self-tests ------------------------------------------------------------------------


def _fake_credentials():
    """[(kind, a line holding one, the part a failure must never show)].

    Put together from fragments, so that no line of this file matches.
    """
    digits = "1234567890"
    hex64 = "0123456789abcdef" * 4
    mixed = "AbCdEfGhIjKlMnOp"
    password = "fake" + "-pw-" + "0000"
    slack = "xo" + "xb-" + digits + "-" + digits + "123-" + mixed + "QrStUvWx"
    app = "xa" + "pp-1-A" + digits + "-" + digits + "123-" + hex64
    webhook = "https://hooks" + ".slack.com/services/T" + digits + "/B" + digits + "/" + mixed
    brevo = "xkey" + "sib-" + hex64 + "-" + mixed
    smtp = "xsmtp" + "sib-" + hex64 + "-" + mixed
    github = "gh" + "p_" + mixed + mixed + "AbCd"
    fine_grained = "github" + "_pat_" + mixed + "AbCdEf" + "_" + (mixed * 4)[:59]
    aws = "AK" + "IA" + mixed.upper()
    pem = "-----BEGIN " + "OPENSSH PRIVATE " + "KEY-----"
    return [
        ("Slack token", f'token = "{slack}"', slack),
        ("Slack app token", f"SLACK_APP_TOKEN={app}", app),
        ("Slack webhook URL", f"curl -X POST {webhook}", webhook),
        ("Brevo key", f"api-key: {brevo}", brevo),
        ("Brevo key", f"smtp: {smtp}", smtp),
        ("GitHub token", f"GH_TOKEN={github}", github),
        ("GitHub token", f"token: {fine_grained}", fine_grained),
        ("AWS access key id", f"aws_access_key_id = {aws}", aws),
        ("private key block", pem, pem),
        ("password after sshpass -p", "ssh" + "pass -p " + password + " ssh pi@rrr", password),
        ("password after sshpass -p", "ssh" + "pass -e -p'" + password + "' ssh", password),
        (
            "password after sshpass -p",
            '"Bash(ssh' + 'pass -p \\"' + password + '\\" ssh pi@rrr:*)"',
            password,
        ),
        ("password in SUDO_PWD", "export SUDO" + "_PWD=" + password, password),
        ("password in SUDO_PWD", "SUDO" + '_PWD = "' + password + '"', password),
        ("password in SSHPASS", "SSH" + "PASS='" + password + "' sshpass -e ssh", password),
        (
            "password echoed into sudo -S",
            "ec" + "ho " + password + " | sudo" + " -S true",
            password,
        ),
        (
            "password echoed into sudo -S",
            "ec" + 'ho "' + password + '" | sudo -u root' + " -S apt-get update",
            password,
        ),
    ]


@pytest.mark.parametrize(
    "kind, line, _value",
    _fake_credentials(),
    # ids name the kind only, so the samples stay out of the test report
    ids=[f"{number}-{kind}" for number, (kind, _, _) in enumerate(_fake_credentials())],
)
def test_each_kind_of_credential_is_found(kind, line, _value):
    assert hits_in("first line\n" + line + "\nlast line\n") == [(2, kind)]


@pytest.mark.parametrize(
    "line",
    [
        'save_credentials("xoxb-test", "C0123")',  # test_secrets.py's fixtures
        'token = "xoxb-123-test-token"',
        "xoxb-not-a-real-token",
        "Slack posts to hooks.slack.com",
        "ghp_short",
        "AKIA plus sixteen",
        "-----BEGIN PUBLIC KEY-----",
        "-----BEGIN CERTIFICATE-----",
        'sshpass -p "$RRR_PI_PASSWORD" ssh pi@rrr',
        "sshpass -p $PW ssh pi@rrr",
        "sshpass -p <password> ssh pi@rrr",
        "sshpass -p xxx ssh pi@rrr",
        "sshpass -f ~/.pi-password ssh pi@rrr",
        "sshpass -e ssh pi@rrr",
        "never `sshpass -p`, never a password",
        'SUDO_PWD="${SUDO_PWD:-}"',
        "SUDO_PWD=$(cat ~/.sudo-password)",
        'SUDO_PWD = os.environ["SUDO_PWD"]',
        "SUDO_PWD=",
        'echo "$SUDO_PWD" | sudo -S true',
        "echo done | sudo tee /etc/rrr.conf",
        "echo 1 | sudo ls -lS",
        "echo pw | grep p | sudo -S true",
    ],
)
def test_placeholders_and_look_alikes_are_not_credentials(line):
    assert hits_in(line) == []


def test_a_failure_names_file_line_and_kind_but_never_the_value(tmp_path):
    samples = _fake_credentials()
    (tmp_path / "notes.md").write_text(
        "nothing here\n" + "\n".join(line for _, line, _ in samples) + "\n", encoding="utf-8"
    )
    found = findings(tmp_path, ["notes.md"])
    message = report(found, "a test tree")
    assert found == [
        f"notes.md:{number}: {kind}" for number, (kind, _, _) in enumerate(samples, start=2)
    ]
    for _, _, value in samples:
        assert value not in message


def test_an_allowed_entry_lets_its_kind_through_in_its_file_only(tmp_path, monkeypatch):
    kind, line, _ = _fake_credentials()[3]  # a Brevo key
    for name in ("fixture.txt", "other.txt"):
        (tmp_path / name).write_text(line + "\n", encoding="utf-8")
    monkeypatch.setitem(ALLOWED, "fixture.txt", (kind, "a fixture"))
    assert findings(tmp_path, ["fixture.txt", "other.txt"]) == [f"other.txt:1: {kind}"]


@pytest.mark.parametrize(
    "relative, kind",
    [
        (".claude/settings.json", "Claude Code settings file"),
        (".claude/settings.local.json", "Claude Code settings file"),
        ("Project/.claude/settings.json", "Claude Code settings file"),
        ("secrets.json", "secrets file"),
        ("Project/secrets.json", "secrets file"),
        ("Project/rrr_database.db", "SQLite database"),
        ("backups/rrr.sqlite3", "SQLite database"),
        ("Project/settings/settings.json", "device settings file"),
        (".env", "environment file"),
        ("deploy/server.pem", "PEM or key file"),
        ("tls.key", "PEM or key file"),
        ("id_rsa", "SSH key file"),
        ("keys/id_ed25519.pub", "SSH key file"),
        (".claude/skills/release-and-versioning/SKILL.md", None),
        ("Project/utils/secrets.py", None),
        ("Project/tests/unit/test_secrets.py", None),
        ("Project/settings/README.md", None),
        ("settings.json", None),
        (".env.example", None),
        ("docs/keyboard.md", None),
    ],
)
def test_which_paths_hold_credentials(relative, kind):
    assert banned_path_kind(relative) == kind


def _make_tree(root):
    for name in (
        "Project/main.py",
        "scripts/install.sh",
        "Project/__pycache__/main.cpython-311.pyc",
        ".venv/lib/site.py",
        "dist/rrr.rrrupdate",
        ".claude/worktrees/feature/Project/main.py",
        ".git/config",
    ):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x\n", encoding="utf-8")


def test_without_a_git_directory_every_file_under_the_root_is_checked(tmp_path):
    _make_tree(tmp_path)
    (tmp_path / ".git" / "config").unlink()
    (tmp_path / ".git").rmdir()
    files, listed = list_files(tmp_path)
    assert files == ["Project/main.py", "scripts/install.sh"]
    assert "no .git" in listed


@pytest.mark.parametrize(
    "outcome, said",
    [
        (FileNotFoundError(2, "No such file or directory", "git"), "git could not run"),
        (
            subprocess.CompletedProcess(
                [], 128, b"", b"fatal: detected dubious ownership in repository at '/__w/r'\n"
            ),
            "dubious ownership",
        ),
        (subprocess.CompletedProcess([], 0, b"", b""), "listed nothing"),
    ],
    ids=["no git", "dubious ownership", "nothing listed"],
)
def test_when_git_cannot_list_the_files_every_file_is_checked(
    tmp_path, monkeypatch, outcome, said
):
    _make_tree(tmp_path)

    def run(*_args, **_kwargs):
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(subprocess, "run", run)
    files, listed = list_files(tmp_path)
    assert files == ["Project/main.py", "scripts/install.sh"]
    assert said in listed
