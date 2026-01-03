import re
from typing import Optional, Tuple

ATCODER_URL_RE = re.compile(
    r"atcoder\.jp/contests/([^/]+)/tasks/([^/?#]+)", re.IGNORECASE
)
LEETCODE_URL_RE = re.compile(
    r"leetcode\.(?:com|cn)/problems/([^/?#]+)", re.IGNORECASE
)
ATCODER_ID_RE = re.compile(r"^(abc|arc|agc|ahc)\d+_[a-z]\d*$", re.IGNORECASE)
CF_ID_RE = re.compile(r"^\d+[A-Za-z]$")


def detect_source(problem_id: str, explicit_source: Optional[str] = None) -> Tuple[str, str]:
    """
    Infer problem source and normalized id from user input.
    """
    if problem_id is None:
        return "unknown", ""

    pid = str(problem_id).strip()
    if not pid:
        return "unknown", ""

    if "://" in pid:
        match = ATCODER_URL_RE.search(pid)
        if match:
            return "atcoder", match.group(2).lower()
        match = LEETCODE_URL_RE.search(pid)
        if match:
            return "leetcode", match.group(1)
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

    if pid.upper().startswith("P") and pid[1:].isdigit():
        return "luogu", pid.upper()

    return "leetcode", pid


def looks_like_problem_id(problem_id: str) -> bool:
    if problem_id is None:
        return False
    pid = str(problem_id).strip()
    if not pid:
        return False
    if ":" in pid and len(pid.split(":")) == 2:
        source, pid = pid.split(":", 1)
        return source.lower() in ["atcoder", "leetcode", "codeforces", "luogu"] and looks_like_problem_id(pid)
    if pid.isdigit():
        return True
    if ATCODER_ID_RE.match(pid):
        return True
    if pid.upper().startswith("CF") or CF_ID_RE.match(pid):
        return True
    if pid.upper().startswith("P") and pid[1:].isdigit():
        return True
    return False
