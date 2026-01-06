import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag


def table_to_markdown(table: Tag) -> str:
    rows = []
    for tr in table.find_all("tr"):
        cells = [cell.get_text(" ", strip=True) for cell in tr.find_all(["th", "td"])]
        if cells:
            rows.append(cells)
    if not rows:
        return ""
    width = max(len(row) for row in rows)
    normalized = [row + [""] * (width - len(row)) for row in rows]
    header = normalized[0]
    separator = ["---"] * width
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(separator) + " |",
    ]
    for row in normalized[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return "\n" + "\n".join(lines) + "\n"


def normalize_newlines(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text)


def normalize_math_delimiters(text: str) -> str:
    """Convert triple dollar LaTeX delimiters to single dollar."""
    return re.sub(r"\$\$\$([\s\S]+?)\$\$\$", r"$\1$", text)


def fix_relative_urls_in_soup(soup: BeautifulSoup, base_url: str) -> None:
    for img in soup.find_all("img", src=True):
        img["src"] = urljoin(base_url, img["src"])
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if href.startswith(("#", "javascript:", "mailto:")):
            continue
        link["href"] = urljoin(base_url, href)
