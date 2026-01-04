import re
from typing import Optional, Tuple

VALID_PREFIX_SOURCES = {"atcoder", "leetcode", "codeforces", "luogu", "uva", "spoj"}

ATCODER_URL_RE = re.compile(
    r"atcoder\.jp/contests/([^/]+)/tasks/([^/?#]+)", re.IGNORECASE
)
LEETCODE_URL_RE = re.compile(
    r"leetcode\.(?:com|cn)/(?:contest/[^/]+/)?problems/([^/?#]+)", re.IGNORECASE
)
# Added protocol support and word boundary anchor
CODEFORCES_URL_RE = re.compile(
    r"\b(?:https?://)?(?:www\.)?codeforces\.com/(?:contest/(\d+)/problem/([A-Z0-9]+)|problemset/problem/(\d+)/([A-Z0-9]+))",
    re.IGNORECASE
)
LUOGU_URL_RE = re.compile(
    r"luogu\.com\.cn/problem/([A-Z0-9_]+)", re.IGNORECASE
)

ATCODER_ID_RE = re.compile(r"^(abc|arc|agc|ahc)\d+_[a-z]\d*$", re.IGNORECASE)
CF_ID_RE = re.compile(r"^\d+[A-Za-z]$")

# Refined Luogu ID patterns:
# - CF: CF + digits + letter (e.g. CF1234A)
# - AT: AT_ + standard AtCoder ID
# - Internal: P, B, U, T + digits
# - External: UVA, SP + digits
LUOGU_ID_RE = re.compile(
    r"^([PBTU]\d+|CF\d+[A-Z]|AT_(?:abc|arc|agc|ahc)\d+_[a-z]\d*|UVA\d+|SP\d+)$",
    re.IGNORECASE,
)


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
        # Groups: 1=Contest, 2=Index (type 1) OR 3=Contest, 4=Index (type 2)
        contest_id = match.group(1) or match.group(3)
        index = match.group(2) or match.group(4)
        return "codeforces", f"{contest_id}{index}".upper()
    match = LUOGU_URL_RE.search(pid)
    if match:
        # For Luogu URLs, we check the ID to see if it belongs to another platform
        luogu_pid = match.group(1).upper()
        if luogu_pid.startswith("CF"):
            return "codeforces", luogu_pid
        if luogu_pid.startswith("AT"):
            # Correctly remove AT_ prefix case-insensitively
            # Since luogu_pid is upper case here, we can strip "AT_"
            if luogu_pid.startswith("AT_"):
                 return "atcoder", luogu_pid[3:].lower()
            return "atcoder", luogu_pid.lower()
        return "luogu", luogu_pid

    # If it's a URL but not from a recognized platform, return unknown
    if "://" in pid:
        return "unknown", pid

    # Prefix detection with validation
    if pid.count(":") == 1:
        source, raw_id = pid.split(":", 1)
        if source.lower() in VALID_PREFIX_SOURCES:
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

    if ":" in pid:
        parts = pid.split(":", 1)
        if len(parts) == 2:
            source, sub_pid = parts
            if source.lower() in VALID_PREFIX_SOURCES:
                return looks_like_problem_id(sub_pid)
    
    if pid.isdigit():
        return True
    if ATCODER_ID_RE.match(pid):
        return True
    if pid.upper().startswith("CF") or CF_ID_RE.match(pid):
        return True
    if LUOGU_ID_RE.match(pid):
        return True
    return False