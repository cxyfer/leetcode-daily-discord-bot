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
