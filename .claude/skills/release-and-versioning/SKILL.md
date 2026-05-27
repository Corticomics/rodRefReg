---
name: release-and-versioning
description: Cut a release of RRR safely — bump Project/version.py, tag, push, let CI build the .rrrupdate bundle. Use when the user says "release", "tag", "ship", "bump the version", "cut a version", or asks how the in-app updater finds new builds. Covers SemVer for RRR, when to bump vs. not, recovery from a bad tag, and the hard "tag == v<version>" CI invariant.
---

# Release and versioning

The version lives in **one file**:
[`Project/version.py`](Project/version.py). Everything else (the git tag,
the bundle filename, the GitHub Release title, the in-app updater check)
derives from it.

## The one invariant CI enforces

The git tag MUST equal `v<__version__>` at the tagged commit, byte for
byte. [`.github/workflows/release.yml`](.github/workflows/release.yml)
fails the build otherwise:

```yaml
- name: Verify tag matches Project/version.py
  run: |
    if [[ "${{ steps.ver.outputs.tag }}" != "v${{ steps.ver.outputs.app_version }}" ]]; then
      echo "::error::tag ${{ steps.ver.outputs.tag }} does not match v${{ steps.ver.outputs.app_version }} from Project/version.py"
      exit 1
    fi
```

Pre-release tags use `-beta` (e.g. `v1.7.0-beta`, `v1.7.0-beta.2`); CI
flags them as pre-release, and the in-app updater ignores them unless the
device has opted into the beta channel.

## When to bump (per [MAINTENANCE.md §2](Project/docs/MAINTENANCE.md))

| Level | When | Examples |
|---|---|---|
| PATCH `1.6.x → 1.6.x+1` | bug fix, security pin, internal refactor — anything user-invisible | fix a crash, pin a dep version, tighten an error message |
| MINOR `1.x.y → 1.x+1.0` | new feature, new sub-tab, new opt-in driver | add a tab, ship a new calibration mode |
| MAJOR `x.y.z → x+1.0.0` | breaking change, schema migration that can't roll back, GPIO/hardware change | drop a column for real, change pin layout |

**In doubt → bump the higher level.** It's free to publish a "1.7.0" that
turned out to be PATCH-equivalent; it's expensive to publish "1.6.4"
that was actually breaking.

## When NOT to bump ([§1](Project/docs/MAINTENANCE.md))

- Test-only changes that don't change production code
- Pure documentation
- `.gitignore` / dev-tooling tweaks (per [§3c](Project/docs/MAINTENANCE.md))
- Anything not yet validated on a real Pi

But — there's an explicit override now codified in
[`CLAUDE.md`](CLAUDE.md):

> If the user explicitly lists "bump version" in their instructions for
> this PR, do it — do not skip citing §3c. The explicit instruction
> overrides the test/doc-only exemption.

So if your prompt says "branch, commit, push, PR, bump version", bump.

## The release flow (full recipe in [`references/release-recipe.md`](references/release-recipe.md))

```
1. branch off main with <type>/<slug>
2. make changes, commit conventionally
3. push branch, open PR
4. merge PR through GitHub UI
5. on local main: git pull --ff-only
6. bump Project/version.py     ← if this PR is release-bound
7. git tag v<new_version>       ← still local; reversible
8. git push origin v<new_version>   ← POINT OF NO RETURN
```

After step 8 the GitHub Actions release workflow builds the bundle
(via [`scripts/release/build-bundle.sh`](scripts/release/build-bundle.sh)),
creates the GitHub Release with the `.rrrupdate` + `.sha256` + `latest.json`
assets attached, and devices on the stable channel see "Update available"
in [`Project/ui/UpdatesTab.py`](Project/ui/UpdatesTab.py).

## What the bundle contains

`scripts/release/build-bundle.sh` runs `git archive HEAD Project scripts
requirements.txt` and packs it as `rrr-<version>.rrrupdate` (tar.gz).
That means:

- Top-level `README.md`, `CLAUDE.md`, `install.sh`, and `bootstrap.sh`
  are **not shipped** to devices via the update path.
- `Project/settings/settings.json`, `*.db`, and `.DS_Store` are stripped
  even if you accidentally tracked them.
- The bundle reflects committed state, not your working tree. **Always
  commit before tagging.**

## When something goes wrong

`references/recovery-recipes.md` covers:

- mis-tagged commit, tag not yet pushed → just retag locally
- pushed a bad tag, CI rejected → delete the local + remote tag, fix,
  retry
- a bad release IS published → bump and ship a fix; don't try to
  unpublish
- CI says "tag does not match" → re-read [§6.4](Project/docs/MAINTENANCE.md#64-ci-rejected-the-tag-with-tag-does-not-match-projectversionpy)

## Hard rules

- Pull `main` before tagging. `git tag` is silent about which commit
  it marks; on a stale `main` you tag the wrong commit and CI rejects
  it ([§6.2](Project/docs/MAINTENANCE.md#62-you-pushed-a-bad-tag-no-release-exists-yet-ci-rejected-it)).
- Never amend a pushed commit; never force-push to `main`. If a hook
  rejects a commit, fix the issue and create a NEW commit.
- Never ship updates via `git pull` to a device. Tagged GitHub Releases
  are the only supported channel; CI owns `dist/`.
- Never tag a commit whose Tests workflow is red. The release workflow
  itself doesn't gate on it, so this is a discipline rule, not a CI rule.
- Never publish a release that hasn't been validated on a real Pi
  (§1, rule above).
