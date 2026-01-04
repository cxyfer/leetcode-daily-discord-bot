import re
from typing import Optional, Tuple

ATCODER_URL_RE = re.compile(
    r"atcoder\.jp/contests/([^/]+)/tasks/([^/?#]+)", re.IGNORECASE
)
LEETCODE_URL_RE = re.compile(
    r"leetcode\.(?:com|cn)/(?:contest/[^/]+/)?problems/([^/?#]+)", re.IGNORECASE
)
CODEFORCES_URL_RE = re.compile(
    r"codeforces\.com/(?:contest/\d+/problem|problemset/problem)/([^/?#]+)", re.IGNORECASE
)
LUOGU_URL_RE = re.compile(
    r"luogu\.com\.cn/problem/([A-Z0-9_]+)", re.IGNORECASE
)

ATCODER_ID_RE = re.compile(r"^(abc|arc|agc|ahc)\d+_[a-z]\d*$", re.IGNORECASE)
CF_ID_RE = re.compile(r"^\d+[A-Za-z]$")
# Luogu supports P, B, U, T (internal), plus externally sourced CF, AT, UVA, SP
LUOGU_ID_RE = re.compile(r"^([PBTU]\d+|CF[0-9A-Z]+|AT_[a-z0-9_]+|UVA\d+|SP\d+)$", re.IGNORECASE)


def detect_source(problem_id: str, explicit_source: Optional[str] = None) -> Tuple[str, str]:
    """
    Infer problem source and normalized id from user input.
    """
    if problem_id is None:
        return "unknown", ""

    pid = str(problem_id).strip()
    if not pid:
        return "unknown", ""

    # URL detection
    match = ATCODER_URL_RE.search(pid)
    if match:
        return "atcoder", match.group(2).lower()
    match = LEETCODE_URL_RE.search(pid)
    if match:
        return "leetcode", match.group(1)
    match = CODEFORCES_URL_RE.search(pid)
    if match:
        return "codeforces", match.group(1).upper()
    match = LUOGU_URL_RE.search(pid)
    if match:
        # For Luogu URLs, we check the ID to see if it belongs to another platform
        luogu_pid = match.group(1).upper()
        if luogu_pid.startswith("CF"):
            return "codeforces", luogu_pid
        if luogu_pid.startswith("AT"):
            return "atcoder", luogu_pid.lower().replace("at_", "")
        return "luogu", luogu_pid

    # If it's a URL but not from a recognized platform, return unknown
    if "://" in pid:
        return "unknown", pid

    if ":" in pid:
        source, raw_id = pid.split(":", 1)
        if source:
            return source.lower(), raw_id

    if explicit_source:
        return explicit_source.lower(), pid

    if pid.isdigit():
        return "leetcode", pid

    if ATCODER_ID_RE.match(pid):
        return "atcoder", pid.lower()

    if pid.upper().startswith("CF") or CF_ID_RE.match(pid):
        return "codeforces", pid.upper()

    # Luogu-specific patterns
    if LUOGU_ID_RE.match(pid):
        return "luogu", pid.upper()

    return "leetcode", pid


def looks_like_problem_id(problem_id: str) -> bool:
    if problem_id is None:
        return False
    pid = str(problem_id).strip()
    if not pid:
        return False
    
    # Treat platform URLs as valid problem identifiers
    if (LEETCODE_URL_RE.search(pid) or 
        ATCODER_URL_RE.search(pid) or 
        CODEFORCES_URL_RE.search(pid) or 
        LUOGU_URL_RE.search(pid)):
        return True

    # If it's a URL but not from a recognized platform, it doesn't look like a problem ID
    if "://" in pid:
        return False

    if ":" in pid and len(pid.split(":")) == 2:
        source, sub_pid = pid.split(":", 1)
        valid_sources = ["atcoder", "leetcode", "codeforces", "luogu", "uva", "spoj"]
        return source.lower() in valid_sources and looks_like_problem_id(sub_pid)
    
    if pid.isdigit():
        return True
    if ATCODER_ID_RE.match(pid):
        return True
    if pid.upper().startswith("CF") or CF_ID_RE.match(pid):
        return True
    if LUOGU_ID_RE.match(pid):
        return True
    return False
