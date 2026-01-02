import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.source_detector import detect_source


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


def test_detect_source_prefix():
    source, pid = detect_source("atcoder:abc001_a")
    assert source == "atcoder"
    assert pid == "abc001_a"


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


def test_detect_source_luogu_pattern():
    source, pid = detect_source("p1001")
    assert source == "luogu"
    assert pid == "P1001"


def test_detect_source_unknown_url():
    source, pid = detect_source("https://example.com/problems/1")
    assert source == "unknown"
    assert pid == "https://example.com/problems/1"
