import sys
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.html_converter import (
    fix_relative_urls_in_soup,
    normalize_math_delimiters,
    normalize_newlines,
    table_to_markdown,
)


def test_table_to_markdown_basic():
    html = """
    <table>
      <tr><th>A</th><th>B</th></tr>
      <tr><td>1</td><td>2</td></tr>
    </table>
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    result = table_to_markdown(table)

    assert "| A | B |" in result
    assert "| --- | --- |" in result
    assert "| 1 | 2 |" in result


def test_table_to_markdown_empty():
    html = "<table></table>"
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    result = table_to_markdown(table)

    assert result == ""


def test_table_to_markdown_uneven_rows():
    html = """
    <table>
      <tr><th>A</th><th>B</th><th>C</th></tr>
      <tr><td>1</td><td>2</td></tr>
    </table>
    """
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    result = table_to_markdown(table)

    assert "| A | B | C |" in result
    assert "| 1 | 2 |  |" in result


def test_normalize_newlines_basic():
    text = "a\n\n\nb\n\n\n\nc"
    result = normalize_newlines(text)

    assert result == "a\n\nb\n\nc"


def test_normalize_newlines_preserves_double():
    text = "a\n\nb"
    result = normalize_newlines(text)

    assert result == "a\n\nb"


def test_fix_relative_urls_in_soup_images():
    html = '<img src="/images/test.png">'
    soup = BeautifulSoup(html, "html.parser")
    fix_relative_urls_in_soup(soup, "https://example.com")

    img = soup.find("img")
    assert img["src"] == "https://example.com/images/test.png"


def test_fix_relative_urls_in_soup_links():
    html = '<a href="/page">Link</a>'
    soup = BeautifulSoup(html, "html.parser")
    fix_relative_urls_in_soup(soup, "https://example.com")

    link = soup.find("a")
    assert link["href"] == "https://example.com/page"


def test_fix_relative_urls_in_soup_skips_special():
    html = '<a href="#anchor">Anchor</a><a href="javascript:void(0)">JS</a><a href="mailto:test@example.com">Email</a>'
    soup = BeautifulSoup(html, "html.parser")
    fix_relative_urls_in_soup(soup, "https://example.com")

    links = soup.find_all("a")
    assert links[0]["href"] == "#anchor"
    assert links[1]["href"] == "javascript:void(0)"
    assert links[2]["href"] == "mailto:test@example.com"


def test_fix_relative_urls_in_soup_protocol_relative():
    html = '<img src="//cdn.example.com/img.png">'
    soup = BeautifulSoup(html, "html.parser")
    fix_relative_urls_in_soup(soup, "https://example.com")

    img = soup.find("img")
    assert img["src"] == "https://cdn.example.com/img.png"


def test_normalize_math_delimiters_triple_to_single():
    text = "The value is $$$x + y$$$."
    result = normalize_math_delimiters(text)
    assert result == "The value is $x + y$."


def test_normalize_math_delimiters_preserves_double():
    text = "Display: $$x^2$$"
    result = normalize_math_delimiters(text)
    assert result == "Display: $$x^2$$"
