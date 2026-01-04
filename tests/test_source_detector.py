import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.source_detector import CF_ID_RE, detect_source, looks_like_problem_id


def test_detect_source_atcoder_url():
    source, pid = detect_source(
        "https://atcoder.jp/contests/abc001/tasks/abc001_a"
    )
    assert source == "atcoder"
    assert pid == "abc001_a"


def test_detect_source_leetcode_url():
    source, pid = detect_source("https://leetcode.com/problems/two-sum/")
    assert source == "leetcode"
    assert pid == "two-sum"


def test_detect_source_leetcode_cn_url():
    source, pid = detect_source("https://leetcode.cn/problems/two-sum/")
    assert source == "leetcode"
    assert pid == "two-sum"


def test_detect_source_leetcode_contest_url():
    # Contest URL
    source, pid = detect_source(
        "https://leetcode.cn/contest/biweekly-contest-173/problems/minimum-subarray-length-with-distinct-sum-at-least-k/"
    )
    assert source == "leetcode"
    assert pid == "minimum-subarray-length-with-distinct-sum-at-least-k"


def test_detect_source_leetcode_description_url():
    # Description suffix
    source, pid = detect_source(
        "https://leetcode.cn/problems/maximum-building-height/description/"
    )
    assert source == "leetcode"
    assert pid == "maximum-building-height"


def test_detect_source_codeforces_url():
    source, pid = detect_source(
        "https://codeforces.com/contest/1234/problem/A"
    )
    assert source == "codeforces"
    assert pid == "1234A"
    
    source, pid = detect_source(
        "https://codeforces.com/problemset/problem/1234/B"
    )
    assert source == "codeforces"
    assert pid == "1234B"


def test_detect_source_luogu_urls():
    # Normal Luogu Problem
    source, pid = detect_source("https://www.luogu.com.cn/problem/P1001")
    assert source == "luogu"
    assert pid == "P1001"

    # UVA
    source, pid = detect_source("https://www.luogu.com.cn/problem/UVA100")
    assert source == "luogu"
    assert pid == "UVA100"
    
    # B-series
    source, pid = detect_source("https://www.luogu.com.cn/problem/B2001")
    assert source == "luogu"
    assert pid == "B2001"
    
    # CF in Luogu -> redirects to Codeforces source logic
    source, pid = detect_source("https://www.luogu.com.cn/problem/CF1C")
    assert source == "codeforces"
    assert pid == "CF1C"
    
    # AT in Luogu -> redirects to AtCoder source logic
    source, pid = detect_source("https://www.luogu.com.cn/problem/AT_agc001_a")
    assert source == "atcoder"
    assert pid == "agc001_a"
    
    # SP (SPOJ)
    source, pid = detect_source("https://www.luogu.com.cn/problem/SP1")
    assert source == "luogu"
    assert pid == "SP1"
    
    # U-series (User uploaded)
    source, pid = detect_source("https://www.luogu.com.cn/problem/U360300")
    assert source == "luogu"
    assert pid == "U360300"
    
    # T-series (Team/Internal)
    source, pid = detect_source("https://www.luogu.com.cn/problem/T215441")
    assert source == "luogu"
    assert pid == "T215441"


def test_detect_source_prefix():
    source, pid = detect_source("atcoder:abc001_a")
    assert source == "atcoder"
    assert pid == "abc001_a"

def test_detect_source_invalid_prefix():
    # "invalid" is not a known source, so it should NOT return source="invalid"
    # It will fall through to default behavior (leetcode, or whatever matches)
    source, pid = detect_source("invalid:abc")
    assert source != "invalid"


def test_detect_source_explicit_source():
    source, pid = detect_source("123", explicit_source="codeforces")
    assert source == "codeforces"
    assert pid == "123"


def test_detect_source_numeric_default():
    source, pid = detect_source("123")
    assert source == "leetcode"
    assert pid == "123"


def test_detect_source_atcoder_id_regex():
    source, pid = detect_source("ABC001_A")
    assert source == "atcoder"
    assert pid == "abc001_a"


def test_detect_source_codeforces_patterns():
    source, pid = detect_source("CF1234A")
    assert source == "codeforces"
    assert pid == "CF1234A"

    source, pid = detect_source("1234A")
    assert source == "codeforces"
    assert pid == "1234A"


def test_codeforces_id_regex_complex_index():
    assert CF_ID_RE.match("1999B1")
    assert CF_ID_RE.match("1000G2")
    assert CF_ID_RE.match("CF1999B1")
    assert CF_ID_RE.match("1234A")


def test_detect_source_luogu_ids():
    source, pid = detect_source("P1001")
    assert source == "luogu"
    assert pid == "P1001"

    source, pid = detect_source("B2001")
    assert source == "luogu"
    assert pid == "B2001"

    source, pid = detect_source("UVA100")
    assert source == "luogu"
    assert pid == "UVA100"
    
    # Test CF-like ID in Luogu context
    source, pid = detect_source("CF1234A")
    assert source == "codeforces"
    assert pid == "CF1234A"


def test_detect_source_unknown_url():
    source, pid = detect_source("https://example.com/problems/1")
    assert source == "unknown"
    assert pid == "https://example.com/problems/1"


def test_looks_like_problem_id_detection():
    # URLs
    assert looks_like_problem_id("https://leetcode.com/problems/two-sum/")
    assert looks_like_problem_id("https://leetcode.cn/contest/biweekly-contest-173/problems/problem-id/")
    assert looks_like_problem_id("https://www.luogu.com.cn/problem/P1001")
    assert looks_like_problem_id("https://codeforces.com/contest/1234/problem/A")
    
    # Prefix
    assert looks_like_problem_id("atcoder:abc001_a")
    
    # IDs
    assert looks_like_problem_id("1234")
    assert looks_like_problem_id("abc001_a")
    assert looks_like_problem_id("CF1234A")
    assert looks_like_problem_id("P1001")
    assert looks_like_problem_id("B2001")
    assert looks_like_problem_id("UVA100")
    
    # Non-IDs
    assert not looks_like_problem_id("two sum")
    assert not looks_like_problem_id("https://google.com")
    
    # Negative cases
    assert not looks_like_problem_id("invalid:abc")
    assert not looks_like_problem_id("abc:def:ghi") # "abc" is not a valid source
    
    # Recursive valid case
    # "atcoder:..." is valid if "..." is valid. 
    # "leetcode:123" is valid.
    # So "atcoder:leetcode:123" should be valid.
    assert looks_like_problem_id("atcoder:leetcode:123")
