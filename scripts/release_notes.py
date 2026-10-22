#!/usr/bin/env python3
"""Generate editable English release notes from Git and GitHub pull requests."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

TAG = re.compile(r"v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-rc\.(0|[1-9]\d*))?", re.ASCII)
PR = re.compile(r"\(#([1-9]\d*)\)$|^Merge pull request #([1-9]\d*)\b")
REPO = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9][A-Za-z0-9_.-]*")
BUMP = re.compile(
    r"\b(?:chore|build|release)(?:\(release\))?:\s*"
    r"(?:bump (?:version )?(?:to )?|prepare |release )?"
    r"v?\d+\.\d+\.\d+(?:-rc\.\d+)?(?:\s+\(#\d+\))?$",
    re.IGNORECASE,
)


class ReleaseError(ValueError):
    """An actionable release validation failure."""


def run(*args: str) -> str:
    try:
        result = subprocess.run(args, check=True, text=True, capture_output=True)
    except OSError as error:
        raise ReleaseError(f"Cannot run {args[0]}: {error}") from error
    except subprocess.CalledProcessError as error:
        raise ReleaseError(f"{args[0]} failed: {error.stderr.strip() or error.stdout.strip()}") from error
    return result.stdout.strip()


def version(tag: str) -> tuple[int, int, int, int, int]:
    match = TAG.fullmatch(tag)
    if not match:
        raise ReleaseError(f"Invalid release tag: {tag}; expected vMAJOR.MINOR.PATCH or vMAJOR.MINOR.PATCH-rc.N")
    major, minor, patch, rc = match.groups()
    return int(major), int(minor), int(patch), int(rc is None), int(rc or 0)


def tag_commit(tag: str) -> str:
    version(tag)
    return run("git", "rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}")


def release_tags() -> list[str]:
    return [tag for tag in run("git", "tag", "--list").splitlines() if TAG.fullmatch(tag)]


def is_ancestor(earlier: str, target: str) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", earlier, target],
        text=True,
        capture_output=True,
    )
    if result.returncode not in (0, 1):
        raise ReleaseError(f"Cannot compare tag ancestry: {result.stderr.strip()}")
    return result.returncode == 0


def previous_tag(tag: str, explicit: str | None = None) -> str:
    target = version(tag)
    if explicit is not None:
        tag_commit(explicit)
        if version(explicit) >= target or not is_ancestor(explicit, tag):
            raise ReleaseError("Previous tag must be a lower release version and an ancestor of the target")
        return explicit
    candidates = [
        candidate
        for candidate in release_tags()
        if version(candidate) < target and (not target[3] or version(candidate)[3]) and is_ancestor(candidate, tag)
    ]
    return max(candidates, key=version, default="")


def toml_strings(section: str) -> dict[str, str]:
    # 僅讀取 Python 版本識別所需的單行字串，不引入 TOML 相依套件。
    return dict(re.findall(r"(?m)^\s*(name|version)\s*=\s*[\"']([^\"'\n]+)[\"']\s*(?:#.*)?$", section))


def metadata(tag: str, output: Path) -> None:
    target = version(tag)
    if tag_commit(tag) != run("git", "rev-parse", "HEAD"):
        raise ReleaseError("HEAD must point to the release tag commit")
    root = Path(run("git", "rev-parse", "--show-toplevel"))
    manifest = (root / "pyproject.toml").read_text(encoding="utf-8")
    package = re.search(r"(?ms)^\[project\]\s*\n(.*?)(?=^\[|\Z)", manifest)
    identity = toml_strings(package.group(1) if package else "")
    python_version = tag[1:].replace("-rc.", "rc")
    if not identity.get("name") or identity.get("version") != python_version:
        raise ReleaseError(
            "pyproject.toml [project] name/version does not match the release tag "
            f"(expected Python version {python_version})"
        )
    packages = re.split(r"(?m)^\[\[package\]\]\s*$", (root / "uv.lock").read_text(encoding="utf-8"))[1:]
    locked = [toml_strings(part) for part in packages if toml_strings(part).get("name") == identity["name"]]
    if len(locked) != 1 or locked[0].get("version") != python_version:
        raise ReleaseError("uv.lock root package version does not match the release tag")
    tags = release_tags()
    stable = [candidate for candidate in tags if version(candidate)[3]]
    values = {
        "tag": tag,
        "version": tag[1:],
        "prerelease": str(not target[3]).lower(),
        "previous_tag": previous_tag(tag),
        "is_latest": str(tag == max(tags, key=version)).lower(),
        "is_latest_stable": str(bool(target[3]) and tag == max(stable, key=version, default="")).lower(),
    }
    with output.open("a", encoding="utf-8") as handle:
        handle.write("".join(f"{key}={value}\n" for key, value in values.items()))


def history(tag: str, previous: str = "") -> list[tuple[str, str]]:
    revision = f"{previous}..{tag}" if previous else tag
    return [
        tuple(line.split("\t", 1))
        for line in run("git", "log", "--first-parent", "--reverse", "--format=%H%x09%s", revision).splitlines()
    ]


def pull_number(subject: str) -> int | None:
    match = PR.search(subject)
    return int(match.group(1) or match.group(2)) if match else None


def markdown(text: str) -> str:
    return re.sub(r"([\\`*_\[\]])", r"\\\1", " ".join(text.split()))


def generate(tag: str, repo: str, output: Path, previous: str | None = None) -> None:
    tag_commit(tag)
    if not REPO.fullmatch(repo):
        raise ReleaseError("Repository must use OWNER/REPO format")
    if output.exists():
        raise ReleaseError(f"Refusing to overwrite existing notes: {output}")
    baseline = previous_tag(tag, previous)
    entries = [(sha, subject) for sha, subject in history(tag, baseline) if not BUMP.search(subject)]
    cache: dict[int, dict[str, str]] = {}

    def pull(number: int) -> dict[str, str]:
        if number not in cache:
            try:
                data = json.loads(run("gh", "api", f"repos/{repo}/pulls/{number}"))
                title, login, url = (
                    data["title"],
                    data["user"]["login"],
                    data["html_url"],
                )
                valid = (
                    isinstance(title, str)
                    and title.strip()
                    and isinstance(login, str)
                    and re.fullmatch(r"[A-Za-z0-9-]+(?:\[bot\])?", login)
                    and isinstance(url, str)
                    and url.casefold() == f"https://github.com/{repo}/pull/{number}".casefold()
                )
                if not valid:
                    raise ValueError("missing or invalid title, user.login or html_url")
            except (ValueError, KeyError, TypeError) as error:
                raise ReleaseError(f"Invalid GitHub metadata for PR #{number}: {error}") from error
            cache[number] = {"title": title, "login": login, "url": url}
        return cache[number]

    numbers = list(dict.fromkeys(number for _, subject in entries if (number := pull_number(subject))))
    pulls = {number: pull(number) for number in numbers}
    complete_history = run("git", "rev-parse", "--is-shallow-repository") == "false"
    earlier = (
        {pull(number)["login"].casefold() for _, subject in history(baseline) if (number := pull_number(subject))}
        if complete_history and baseline and numbers
        else set()
    )
    base_url = f"https://github.com/{repo}"
    lines = [
        "> [!IMPORTANT]",
        f"> Container image: `ghcr.io/{repo}:{tag}`.",
        ">",
        "> TODO: Summarize the purpose and user impact of this release.",
        ">",
        "> TODO: Describe upgrade steps and compatibility considerations.",
    ]
    if not version(tag)[3]:
        lines += [
            ">",
            "> This is a release candidate intended for testing. It may contain issues and is not a stable release.",
        ]
    lines += [
        "",
        "## Highlights",
        "",
        "- TODO: Describe a key improvement and why it matters.",
        "",
        "---",
        "",
        "## What's Changed",
        "",
    ]
    seen: set[int] = set()
    newcomers: list[str] = []
    for sha, subject in entries:
        number = pull_number(subject)
        if number is None:
            lines.append(f"- {markdown(subject)} ([{sha[:7]}]({base_url}/commit/{sha}))")
        elif number not in seen:
            seen.add(number)
            data = pulls[number]
            author = f"[@{data['login']}](https://github.com/{data['login']})"
            link = f"[#{number}]({data['url']})"
            lines.append(f"- {markdown(data['title'])} by {author} in {link}")
            if complete_history and data["login"].casefold() not in earlier:
                newcomers.append(f"- {author} made their first contribution in {link}.")
                earlier.add(data["login"].casefold())
    if not entries:
        lines.append("- No user-facing changes were recorded in this release range.")
    if newcomers:
        lines += ["", "## New Contributors", "", *newcomers]
    changelog = f"compare/{baseline}...{tag}" if baseline else f"commits/{tag}"
    lines += ["", f"**Full Changelog**: {base_url}/{changelog}", ""]
    with output.open("x", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def check(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    errors = []
    if not text.startswith("> [!IMPORTANT]\n"):
        errors.append("Notes must start with an IMPORTANT callout")
    for heading in ("## Highlights", "## What's Changed"):
        if heading not in text.splitlines():
            errors.append(f"Missing required section: {heading}")
    if not re.search(r"(?m)^\*\*Full Changelog\*\*:\s+https://github\.com/\S+$", text):
        errors.append("Missing Full Changelog link")
    if re.search(
        r"\b(?:TODO|TBD|FIXME|REPLACE_ME|PLACEHOLDER|CHANGEME)\b|\{\{[^}\n]+\}\}|[<\[](?:add|insert|describe|replace|your)\b[^>\]\n]*[>\]]",
        text,
        re.IGNORECASE,
    ):
        errors.append("Resolve all TODOs and placeholders before publication")
    previous = ""
    fence = ""
    comment = False
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if fence:
            closing = re.fullmatch(r"(`{3,}|~{3,})", stripped)
            if closing and closing[1][0] == fence[0] and len(closing[1]) >= len(fence):
                fence = ""
            continue
        if comment or stripped.startswith("<!--"):
            comment = "-->" not in stripped
            previous = ""
            continue
        marker = re.match(r"(`{3,}|~{3,})", stripped)
        if marker:
            fence = marker[1]
            previous = ""
            continue
        quoted = stripped.startswith(">")
        content = stripped[1:].strip() if quoted else stripped
        if not content or re.match(r"^(?:#{1,6}\s|\[![A-Z]+\]$|[-*_]{3,}$|\|)", content):
            previous = ""
            continue
        bullet = bool(re.match(r"(?:[-*+]|\d+[.)])\s+", content))
        kind = "quote" if quoted else "prose"
        if not bullet and previous == kind:
            errors.append(
                f"Hard-wrapped prose or bullet continuation at line {number}; "
                "keep each paragraph and bullet on one source line"
            )
        previous = kind
    if errors:
        raise ReleaseError("\n".join(errors))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    meta = commands.add_parser("metadata", help="Validate a checked-out release tag")
    meta.add_argument("tag")
    meta.add_argument("--github-output", required=True, type=Path)
    notes = commands.add_parser("generate", help="Generate editable English release notes")
    notes.add_argument("tag")
    notes.add_argument("--repo", required=True)
    notes.add_argument("--output", required=True, type=Path)
    notes.add_argument("--previous-tag")
    validate = commands.add_parser("check", help="Check manually edited notes before publication")
    validate.add_argument("file", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "metadata":
            metadata(args.tag, args.github_output)
        elif args.command == "generate":
            generate(args.tag, args.repo, args.output, args.previous_tag)
        else:
            check(args.file)
    except (ReleaseError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
