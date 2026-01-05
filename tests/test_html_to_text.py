import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from leetcode import html_to_text


def test_html_to_text_atcoder_formatting():
    html = """
    <span class="lang-en">
      <div class="part">
        <section>
          <h3>Input</h3>
          <pre><var>N</var> <var>M</var>
<var>A _ 1</var> <var>A _ 2</var></pre>
        </section>
      </div>
      <p><var>1\\leq N\\leq 2\\times 10^5</var> and <var>\\lvert i-j\\rvert</var></p>
    </span>
    """

    output = html_to_text(html)

    assert "## Input" in output
    assert "```" in output
    assert "N M" in output
    assert "A_1 A_2" in output
    assert "A _ 1" not in output
    assert "<=" in output
    assert "*" in output
    assert "i-j" in output
    assert "|" in output


def test_html_to_text_mathjax_commands():
    html = """
    <span class="lang-en">
      <p><var>\\mathrm{query}_i</var> <var>\\text{count}</var> <var>\\mathbf{X}</var></p>
      <p><var>\\mathrm query_j</var></p>
    </span>
    """

    output = html_to_text(html)

    assert "query_i" in output
    assert "count" in output
    assert "X" in output
    assert "query_j" in output
    assert "\\mathrm" not in output
    assert "\\text" not in output


def test_html_to_text_latex_to_plain():
    html = "<p>Given $n \\leq 10^5$ elements.</p>"

    output = html_to_text(html)

    assert "n <= 10^5" in output
    assert "$" not in output


def test_html_to_text_display_math():
    html = "<p>Formula: $$\\sum_{i=1}^{n}$$</p>"

    output = html_to_text(html)

    assert "sum_i=1^n" in output
    assert "$$" not in output
