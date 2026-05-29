# Changelog

Curated, operator-facing summary of each **published** RRR release (a
release = a git tag `v<x.y.z>` with a `.rrrupdate` bundle devices can
install via the in-app Updates tab). One line per release, newest first.

This is the human-readable companion to the auto-generated GitHub release
notes. Versioning follows SemVer for RRR — see
[Project/docs/MAINTENANCE.md §2](Project/docs/MAINTENANCE.md#2-picking-the-version-number--semver-for-rrr).
Test-only / doc-only / tooling-only changes do not get a release and are
not listed here.

---

## 1.8.x — stop-sequence safety + multi-HAT

- **1.8.7** — Fix: the Stop button now ends a running schedule *cleanly*
  in well under a second instead of being force-terminated after a 3 s
  hang. (Root cause: the worker-thread quit signal was queued behind the
  blocked UI thread; switched to a direct connection.)
- **1.8.6** — Fix: a crash in the stop cleanup path (`UnboundLocalError`)
  that prevented the delivery worker from shutting down on Stop.
- **1.8.5** — Fix: creating a staggered schedule failed when the start/end
  time landed on a whole second (no microseconds). Schedule creation now
  parses ISO datetimes robustly.
- **1.8.4** — Internal: temporary timing instrumentation for the Stop
  investigation (removed in 1.8.6).
- **1.8.3** — Fix: Stop now reliably cancels an in-flight delivery instead
  of letting the next chunk start (cancellation token reset moved to
  schedule start; worker cycle loops honor cancellation).
- **1.8.2** — Add: cooperative cancellation in the delivery strategies so
  Stop interrupts a pour promptly.
- **1.8.1** — Fix (safety): on Stop, all relays — including the master
  solenoid — are dropped *first*, before any thread teardown, so the
  hardware can never be left energized if shutdown stalls.
- **1.8.0** — Feature: the Cages tab now paginates by HAT (one tab per
  relay HAT) so multi-HAT setups are fully visible and editable.

## 1.7.x — cleanup, multi-HAT plumbing, update-flow fixes

- **1.7.7** — Fix: changing the relay-HAT count now regenerates the
  cage→relay map (a 2-HAT setup yields 31 cages, not a stale 15).
- **1.7.6** — Fix: the Cages tab now refreshes correctly after a HAT-count
  change (the system controller is wired through to it).
- **1.7.5** — Fix: "Change Relay Hats" updates the Cages tab immediately,
  without an app restart.
- **1.7.4** — Change: simplified the update notifier to the single GitHub
  release-check path; removed the unused legacy local-changelog dialog.
- **1.7.3** — Change: removed a stale ~1.9 MB doc archive from the release
  bundle (smaller, faster updates).
- **1.7.2** — Fix (safety): quitting RRR is now blocked while a delivery
  schedule is running — Stop the schedule first.
- **1.7.1** — Fix: applying an in-app update now reliably loads the new
  version on restart (was occasionally relaunching the old release).
- **1.7.0** — Change: removed unused legacy UI modules (public-surface
  cleanup; no operator-visible behavior change).

## 1.6.x — dead-code cleanup + offline resilience

- **1.6.4** — Change: removed unused/dead code across the app (Tier-0
  cleanup); fixed a latent crash in the "Change Relay Hats" path.
- **1.6.1** — Improve: clearer Slack-status indicator and update-failure
  dialogs (offline-resilience Phase 3).
- **1.6.0** — Add: fail-closed update verification + a network helper so a
  flaky connection can never install an unverifiable bundle (Phase 2).

## 1.5.x — settings persistence + offline groundwork

- **1.5.3** — Add: offline-resilience test harness (Phase 1).
- **1.5.2** — Maintenance release.
- **1.5.1** — Change: Slack credentials moved to a mode-0600 `secrets.json`
  separate from the settings DB (Phase 2.5b).
- **1.5.0** — Change: type-aware settings persistence in SQLite with a
  one-time migration from the legacy `settings.json` (Phase 2.5a).

## 1.0.0 – 1.4.2 — the in-app update system

- **1.4.x** — Update-apply engine, blue-green activation, recovery fixes
  (Phase 2c).
- **1.3.0** — Blue-green release layout under `~/rrr` + data migration
  (Phase 2b).
- **1.2.0** — Centralized data paths via a `paths` module (Phase 2a).
- **1.1.0** — In-app update check + notification banner (Phase 1).
- **1.0.0** — First versioned release; baseline for the update system
  (Phase 0).
