# Blue-green layout

RRR uses a blue-green deployment under `~/rrr/` so updates are atomic and
rollbackable. Full design in
[Project/docs/UPDATE_SYSTEM.md §13](Project/docs/UPDATE_SYSTEM.md).

## The tree

```
~/rrr/
├── current   → releases/v1.6.4       (symlink — the live release)
├── previous  → releases/v1.6.3       (symlink — rollback target)
├── releases/
│   ├── v1.6.4/
│   │   ├── Project/
│   │   └── scripts/
│   └── v1.6.3/
├── shared/
│   ├── venv/        (one venv across all releases)
│   ├── data/        (DB + settings.json + secrets.json)
│   └── logs/        (rrr_app_debug.log, etc.)
└── state/
    └── boot.json    ({"release": "v1.6.4", "fail_count": 0})
```

## Why this shape

- **Atomic swap.** Updating means writing the new release into
  `releases/v<new>/`, then atomically repointing the `current` symlink
  via `ln -sfn` + `mv -T`. No half-applied state.
- **Cheap rollback.** `previous` is just another symlink. If the new
  release fails to boot, swap them back.
- **Shared data and venv.** Releases are stateless app code; the venv
  (slow to rebuild) and the data (operator-owned) live under `shared/`
  and survive every release swap.

## The launcher and the boot sentinel

The stable shim `~/.local/bin/rrr` execs
[`scripts/runtime/launch.sh`](scripts/runtime/launch.sh) inside the
**current** release. The launcher's job:

1. Read `state/boot.json` — get `release` and `fail_count`.
2. If `fail_count >= 2` and `previous` exists → roll back by repointing
   `current` at `previous`. Reset `fail_count = 0`. Re-exec.
3. Otherwise → increment `fail_count`, write `boot.json`, then exec the
   app: `~/rrr/shared/venv/bin/python3 ~/rrr/current/Project/main.py`.
4. The app, once it has started cleanly, resets `fail_count` to 0.

So a release that crashes during startup will only get two retries
before the device falls back to the previous version. From the
operator's point of view, the title bar reverts to the older version
and the app keeps working — no manual intervention required.

The launcher also exports the data path so the app can find it:

```bash
export RRR_HOME
export RRR_DATA="$RRR_HOME/shared/data"
```

[`Project/utils/paths.py`](Project/utils/paths.py) reads `RRR_DATA` for
every path (`database_path()`, `settings_path()`, `secrets_path()`, etc.)
and falls back to legacy locations when unset — that's how a
dev-from-clone run still works.

## How an in-app update lands

[`Project/utils/updater.py`](Project/utils/updater.py) does:

1. Poll `latest.json` from the GitHub Release.
2. Compare versions; if a new one exists, download the
   `.rrrupdate` bundle (`tar.gz`) + `.sha256`.
3. Verify checksum.
4. Extract to `releases/v<new>/`.
5. `pip install -r requirements.txt` *if* `requirements_hash` in the
   bundle's `manifest.json` changed since the live release. Skipped
   otherwise — most releases don't touch deps.
6. Atomic symlink swap: `previous ← current ← v<new>`.
7. Tell the app to quit; launch.sh starts the new release on next
   invocation.

If anything fails before step 6, the working release is untouched.

## Files you must never touch on a device

- `~/rrr/current/...` — gets overwritten on every release.
- `~/rrr/shared/data/rrr_database.db` — the live SQLite DB. Operator data.
- `~/rrr/shared/data/secrets.json` — Slack credentials, mode 0600.
- `~/rrr/state/boot.json` — overwriting this can re-trigger a rollback.

The installer is the only thing that should write under `~/rrr/`; the
running app reads from `~/rrr/current/Project/` and reads/writes under
`~/rrr/shared/data/` via `RRR_DATA`.

## Recovering a stuck device

The boot sentinel handles "release won't start" automatically. For other
failure modes:

| Symptom | Fix |
|---|---|
| Stuck on an old version, won't update | Check `~/.local/state/rrr/install-*.log` for the last installer run; re-run `./install.sh --only 25-layout` |
| Data corrupt after a bad release | `~/rrr/shared/data/` is preserved across rollback; restore from `~/rrr/shared/data/rrr_database.db.bak-*` if available |
| `current` symlink missing | `./install.sh` is idempotent — re-running re-creates it from the local checkout |
