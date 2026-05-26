# Recovery recipes

When a release goes sideways. Full procedures live in
[MAINTENANCE.md §6](Project/docs/MAINTENANCE.md#6-recovery-procedures);
this file is a fast index.

## I tagged the wrong commit (tag not yet pushed)

Easy. Tags are local until pushed. Delete and re-tag.

```bash
git tag -d v1.7.0                 # remove local
git checkout <correct-commit>
git tag v1.7.0
```

See [§6.1](Project/docs/MAINTENANCE.md#61-you-tagged-the-wrong-commit--tag-not-yet-pushed).

## I pushed a bad tag and CI rejected it (no Release exists)

Common cause: `Project/version.py` says `1.6.3` but you tagged `v1.6.4`.
Fix:

```bash
git tag -d v1.6.4                       # delete locally
git push origin :refs/tags/v1.6.4       # delete from remote
# fix version.py or pick a different tag, commit, then retag
```

`refs/tags/v1.6.4` is the explicit ref-name form — required for delete.
See [§6.2](Project/docs/MAINTENANCE.md#62-you-pushed-a-bad-tag-no-release-exists-yet-ci-rejected-it).

## A bad release IS published and devices may have it

**Don't try to unpublish.** Devices may already have downloaded the
bundle, and `latest.json` on a future request from a slow device might
still point at the bad version.

Instead, ship a fix forward:

1. Bump `Project/version.py` (PATCH if the fix is small).
2. Cut a new release with the corrected behavior.
3. Devices on the bad release will hit it within the polling window
   (default 1 h, see `Project/utils/updater.py`).
4. The boot sentinel in
   [`scripts/runtime/launch.sh`](scripts/runtime/launch.sh) auto-rolls
   back any release that fails to start twice — so a *truly* broken
   release self-recovers without operator action.

Full guidance: [§6.3](Project/docs/MAINTENANCE.md#63-a-bad-release-is-published-and-devices-may-have-it).

## CI rejected: "tag does not match Project/version.py"

The check in
[`.github/workflows/release.yml`](.github/workflows/release.yml) lines
27-33 enforces `tag == v<version>` byte-for-byte. Common gotchas:

- Trailing whitespace in `version.py` (`__version__ = "1.6.4 "`).
- Forgot to pull `main` before tagging → tagged an old commit whose
  `version.py` is older than the new tag.
- Bumped `version.py` on the branch but never merged it.

Fix locally, delete + re-push the tag (see "bad tag" recipe above).
[§6.4](Project/docs/MAINTENANCE.md#64-ci-rejected-the-tag-with-tag-does-not-match-projectversionpy).

## The bundle won't download or verify on a device

Symptoms: app says "checksum mismatch" or "download failed". Check:

1. [`Project/utils/update_failure.py`](Project/utils/update_failure.py)
   classifies the failure. `INTERNET` = network; `VERIFY` = checksum
   or signature; `GENERIC` = anything else.
2. The bundle's `.sha256` and the actual asset must agree —
   `build-bundle.sh` writes both atomically, so a mismatch usually means
   the upload to GitHub Release was partial. Solution: re-upload the
   assets via `gh release upload` or cut a new release.
3. If the bundle downloads but the signature is null in `latest.json`,
   that's expected — signing is Phase 3 future work. The app does not
   reject on null signature.

[§6.5](Project/docs/MAINTENANCE.md#65-the-bundle-wont-download-or-verify-on-a-device).

## A device got stuck on a bad release and rolled back

The blue-green layout means `~/rrr/current` is a symlink. On two failed
starts, [`scripts/runtime/launch.sh`](scripts/runtime/launch.sh) repoints
it at `~/rrr/previous` and restarts. The operator sees the older version
in the title bar — that's the rollback succeeding, not the bug.

To recover forward, push a fixed release (see "bad release is published"
above). The device will pick it up on the next polling cycle.
