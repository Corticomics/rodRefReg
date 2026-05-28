"""Single source of truth for the application version.

Versioning follows Semantic Versioning (MAJOR.MINOR.PATCH) — see
docs/UPDATE_SYSTEM.md. A release is the git tag ``v<__version__>``; the
release CI workflow rejects any tag whose name does not match this value.
"""

__version__ = "1.7.5"
