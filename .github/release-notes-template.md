# Release notes format

Stable releases and release candidates use the same English-only structure.
The generator fills in the release identity, image reference, change list,
first-time PR contributors and comparison link. Edit the summary, upgrade
guidance and highlights before publishing the draft.

```markdown
> [!IMPORTANT]
> Explain what this release delivers and who should upgrade. Identify release candidates explicitly.
>
> Describe incompatible API changes, changed defaults, configuration updates and any required upgrade steps. Remove this paragraph if none apply.

## Highlights

* **Area**: Explain what users can now do or what behaves differently. Group related changes together.

---

## What's Changed

* Generated PR title, contributor and PR link, or a direct commit with its SHA.

## New Contributors

* Generated first-time PR contributors; omit this section when there are none.

**Full Changelog**: Generated comparison link.
```

Keep each paragraph and bullet on one source line; use editor soft wrapping.
Highlights explain user impact rather than repeating commit subjects. Put
breaking changes and required actions in the initial callout. Do not claim
that an upgrade is compatible or requires no action without checking it.

The generated `What's Changed` section is factual source material. It uses PR
numbers recorded in the tagged Git history and includes direct commits, so it
does not depend on GitHub matching rewritten merge commits. Preserve original
PR links and contributor attribution when editing titles for readability.

Run `python3 scripts/release_notes.py check PATH` before publishing. Draft
placeholders are intentional; unresolved placeholders must not be published.
See [RELEASING.md](../RELEASING.md) for image channels and release commands.
