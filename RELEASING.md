# Releasing LeetCode Daily Discord Bot

Stable releases and release candidates use English release notes in the
[standard format](.github/release-notes-template.md). Both tag types build and
push a GHCR image before creating a GitHub release draft. Maintainers edit and
publish the notes after verifying the image.

## Versions, tags and images

| Python project version | Git tag | Published image | GitHub release |
| --- | --- | --- | --- |
| `2.2.0` | `v2.2.0` | `ghcr.io/cxyfer/leetcode-daily-discord-bot:v2.2.0` | Stable draft |
| `2.2.0rc1` | `v2.2.0-rc.1` | `ghcr.io/cxyfer/leetcode-daily-discord-bot:v2.2.0-rc.1` | Prerelease draft |

Supported tags are `vMAJOR.MINOR.PATCH` and `vMAJOR.MINOR.PATCH-rc.N`.
`pyproject.toml` and the root project package in `uv.lock` must both contain
the corresponding Python version. Use the canonical Python spelling `rc1`
in those files, rather than the tag spelling `-rc.1`.

Only the newest stable tag updates the Docker `latest` image. RCs and rebuilds
of older stable versions publish only their exact image tags. Version ordering
is numeric: `rc.10` follows `rc.2`, and a stable version follows its own RCs.
There are no additional floating major, minor, RC, dev or nightly aliases.

Release builds share a serialized queue so an older in-flight build cannot
finish after a newer release and move `latest` backwards. PR validation uses
separate concurrency groups. RC releases must remain GitHub prereleases;
GitHub's latest release label is reserved for stable releases.

## Prepare a version

1. Update `[project].version` in `pyproject.toml` in a release PR. For example,
   use `2.2.0rc1` for the first release candidate or `2.2.0` for stable.
2. Refresh and commit the lockfile, then verify the project:

   ```bash
   uv lock
   uv sync --frozen --all-extras
   uv run ruff check .
   uv run ruff format --check .
   uv run pytest
   python3 -S scripts/test_release_notes.py -v
   ```

3. Review Discord command changes, configuration defaults, upstream oj-api
   compatibility, database changes and required operator actions. The notes
   generator cannot infer upgrade guidance.
4. Merge the release PR into the intended release branch before tagging. The
   tagged commit must contain the release workflow and helper. Never move or
   reuse a published tag; correct a release with a new version.

## Publish the image and create a draft

After preparing version `2.2.0rc1`, for example:

```bash
git tag --annotate v2.2.0-rc.1 --message v2.2.0-rc.1
git push origin v2.2.0-rc.1
gh run list --workflow ghcr.yml --limit 5
gh run watch RUN_ID --exit-status
```

The workflow tests the helper, validates the version, builds and pushes the
exact image, and then creates an English release draft. RC drafts are marked
as prereleases. If a draft or published release already exists for the tag,
the workflow preserves its notes and publication status. API errors fail the
run instead of being treated as a missing release.

Verify the image before publishing the notes:

```bash
docker pull ghcr.io/cxyfer/leetcode-daily-discord-bot:v2.2.0-rc.1
docker image inspect ghcr.io/cxyfer/leetcode-daily-discord-bot:v2.2.0-rc.1
```

For a retry or explicit rebuild of an existing tag containing this tooling:

```bash
gh workflow run ghcr.yml --ref main -f tag=v2.2.0-rc.1
```

The workflow must first be available on the repository's default branch for
manual dispatch. Select a ref containing the current workflow. With no `tag`
input, a manual run only builds and validates an image without pushing or
creating a release. Relevant PRs run the same validation build.

Validation runs the real bot launcher in a disposable container with networking
disabled and no Discord or Gemini credentials. It checks command-module imports,
packaged locale files, fresh SQLite initialization and database integrity. The
expected no-token exit does not prove Discord authentication or delivery.

Successful validation runs retain a `leetcode-daily-discord-bot-validation-image`
artifact for three days. Download and extract the archive, then load it locally:

```bash
docker load --input leetcode-daily-discord-bot-validation-image.tar.gz
```

## Edit and publish the notes

Download the draft, fill in every editorial placeholder, and run the checker:

```bash
tag=v2.2.0-rc.1
notes=/tmp/leetcode-bot-release-notes.md
gh release view "$tag" --json body --jq .body > "$notes"
# Edit the important callout and Highlights in $notes.
python3 scripts/release_notes.py check "$notes"
gh release edit "$tag" --notes-file "$notes" --draft=false --prerelease --latest=false
```

For stable releases, publish with `--prerelease=false` and use `--latest` only
when the release should become GitHub's latest stable release. The generator
does not publish the draft. Publishing notes does not start another container
build; the tag workflow has already pushed the image.

To generate a separate local draft, use a path that does not exist:

```bash
python3 scripts/release_notes.py generate v2.2.0-rc.1 \
  --repo cxyfer/leetcode-daily-discord-bot --output /tmp/leetcode-bot-rc-draft.md
```

Use `--previous-tag v2.1.0` only to deliberately override the automatic range.
The baseline must be an older supported version and an ancestor of the target.
Existing output files are never overwritten.

## Comparison ranges and attribution

- Stable notes compare with the preceding reachable stable version, including
  all changes from the RC cycle.
- RC notes compare with the preceding reachable RC or stable version.
- Unrelated tags and versions newer than the target are excluded.
- A first release includes its available history and links to its commit list.
- PRs are listed once; direct commits include their short SHA.
- First-time PR contributors are checked against preceding represented Git
  history. Shallow history omits unprovable first-contribution claims.

Historical `CHANGELOG.md` entries are retained. Generated notes are not
committed back to the repository or written over manually edited releases.
