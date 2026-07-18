from __future__ import annotations

DEFAULT_DAILY_PUSH_SOURCE = "leetcode.com"
DAILY_PUSH_SOURCE_LABELS = {
    "leetcode.com": "LeetCode",
    "sheep": "Sheep",
    "0x3f": "0x3f",
}
SUPPORTED_DAILY_PUSH_SOURCES = frozenset(DAILY_PUSH_SOURCE_LABELS)


def validate_daily_push_source(source: str) -> str:
    if source not in SUPPORTED_DAILY_PUSH_SOURCES:
        supported = ", ".join(DAILY_PUSH_SOURCE_LABELS)
        raise ValueError(f"Unsupported daily push source: {source}. Expected one of: {supported}")
    return source
