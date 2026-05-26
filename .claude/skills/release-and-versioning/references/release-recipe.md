# Release recipe (the happy path)

Step-by-step. Pause at the line marked "point of no return" before
running it. Long form lives in
[MAINTENANCE.md §3a](Project/docs/MAINTENANCE.md#3a-standard-release--code-change-shipping-to-devices).

## 0. Decide if this is even a release-bound PR

Read [MAINTENANCE.md §1](Project/docs/MAINTENANCE.md#1-when-to-release-and-when-not-to).
If this is test-only, doc-only, or `.gitignore`-only and the user didn't
ask for a bump, **stop here**. Land the PR with no version change.

## 1. Branch & change

```bash
git checkout main
git pull --ff-only origin main
git checkout -b <type>/<short-kebab-slug>   # feat/, fix/, chore/, etc.
# … edit code …
pytest                                      # green or new-test-passes
```

## 2. Conventional commit

```bash
git add <only-the-files-this-PR-touches>
git commit -m "<type>(<scope>): <one-line subject>"
```

No `Co-Authored-By: Claude`, no Claude tagline. The body explains *why*
(not *what*); for a release-bound subject include the target version,
e.g. `feat(offline): … (Phase 3, v1.7.0)`.

## 3. Push & open PR

```bash
git push -u origin <branch>
# Open PR through GitHub UI or `gh pr create`
```

Wait for CI to go green. Review. Squash-merge through the GitHub UI.

## 4. Sync local main

```bash
git checkout main
git pull --ff-only origin main
```

This is the step where forgetting will tag the wrong commit. Don't skip it.

## 5. Bump the version

Edit [`Project/version.py`](Project/version.py) to the new `__version__`
string. Commit:

```bash
git add Project/version.py
git commit -m "chore(version): bump to v<new>"
git push origin main
```

(Or fold the bump into the release-bound PR itself, before merging — the
recent RRR convention is to bump in the same PR that introduces the
behavior change. Either works as long as `main` has the bumped value at
the moment you tag.)

## 6. Tag locally (still reversible)

```bash
git tag v<new_version>
git log -1 v<new_version>     # sanity: confirms tag points at HEAD
```

The tag must equal `v` + the exact string from `Project/version.py` —
case sensitive, no extra whitespace.

## 7. Push the tag — **point of no return**

```bash
git push origin v<new_version>
```

This kicks off [`.github/workflows/release.yml`](.github/workflows/release.yml):

1. Verifies `tag == v<version>` (rejects otherwise).
2. Runs `scripts/release/build-bundle.sh` to produce
   `dist/rrr-<version>.rrrupdate`, `.sha256`, and `latest.json`.
3. Creates the GitHub Release with those three assets attached.
4. Marks pre-release if the tag has `-beta`.

## 8. Verify on a device

- Open the app's Updates tab (`Project/ui/UpdatesTab.py`).
- It should show the new version as available within ~60 s of the
  Release going live.
- Apply, watch the boot sentinel
  ([`scripts/runtime/launch.sh`](scripts/runtime/launch.sh)) NOT roll
  back. If it rolls back twice in a row, devices are now on the previous
  release — investigate via `~/rrr/state/boot.json`.

## Anti-recipe — pre-release / beta

For `1.7.0-beta` etc., everything's the same except:

- `__version__ = "1.7.0-beta"` in `version.py`
- Tag: `v1.7.0-beta`
- GitHub flags it as pre-release
- Stable-channel devices ignore it

Full pre-release rules: [MAINTENANCE.md §2 "Pre-releases"](Project/docs/MAINTENANCE.md#pre-releases--170-beta).
