import logging
import re
from datetime import datetime

import aiohttp
from bs4 import BeautifulSoup

from bot.utils.html_converter import normalize_math_delimiters

logger = logging.getLogger("leetcode")


def generate_history_dates(anchor_date: str, years: int = 5) -> list[str]:
    """
    Generate a list of dates for the same day in previous years.
    Excludes the current year and dates before 2020-04-01.
    """
    if years <= 0:
        return []

    if not re.match(r"^\d{4}-\d{2}-\d{2}$", anchor_date):
        return []

    year, month, day = (int(part) for part in anchor_date.split("-"))
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return []

    if not (month == 2 and day == 29):
        try:
            datetime(year, month, day)
        except ValueError:
            return []

    def is_leap_year(value: int) -> bool:
        return value % 4 == 0 and (value % 100 != 0 or value % 400 == 0)

    min_date = datetime(2020, 4, 1)
    dates: list[str] = []

    for i in range(1, years + 1):
        target_year = year - i
        if month == 2 and day == 29:
            if not is_leap_year(target_year):
                continue
            target_date = datetime(target_year, 2, 29)
            if target_date < min_date and target_date != datetime(2020, 2, 29):
                continue
        else:
            try:
                target_date = datetime(target_year, month, day)
            except ValueError:
                continue
            if target_date < min_date:
                continue

        dates.append(target_date.strftime("%Y-%m-%d"))

    return dates


class LeetCodeClient:
    """LeetCode API Client. Supports both leetcode.com and leetcode.cn."""

    def __init__(self, domain="com"):
        self.domain = domain.lower()
        if self.domain not in ("com", "cn"):
            raise ValueError("Domain must be either 'com' or 'cn'")

        self.base_url = f"https://leetcode.{self.domain}"
        self.graphql_url = f"{self.base_url}/graphql"
        self.session_headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
        }

        logger.info(f"Initialized LeetCode client with domain: leetcode.{self.domain}")

    async def fetch_recent_ac_submissions(self, username, limit=15):
        """
        Fetch recent AC (Accepted) submissions for a given username.

        Args:
            username (str): LeetCode username
            limit (int): Number of submissions to fetch (default: 15)

        Returns:
            list: List of recent AC submissions with basic info (id, title, slug, timestamp)
        """
        if self.domain != "com":
            logger.warning("User submissions are only available on leetcode.com")
            return []

        query = """
        query recentAcSubmissions($username: String!, $limit: Int!) {
            recentAcSubmissionList(username: $username, limit: $limit) {
                id
                title
                titleSlug
                timestamp
            }
        }
        """

        headers = {
            **self.session_headers,
            "Referer": f"{self.base_url}/u/{username}/",
        }

        payload = {
            "query": query,
            "variables": {"username": username, "limit": limit},
            "operationName": "recentAcSubmissions",
        }

        try:
            logger.info(f"Fetching recent AC submissions for user: {username}")

            async with aiohttp.ClientSession() as session:
                async with session.post(self.graphql_url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"API request failed: {response.status} - {error_text}")
                        return []

                    data = await response.json()
                    if "errors" in data:
                        logger.error(f"GraphQL errors: {data['errors']}")
                        return []

                    submissions = data.get("data", {}).get("recentAcSubmissionList", [])
                    logger.info(f"Successfully fetched {len(submissions)} submissions")

                    basic_submissions = []
                    for submission in submissions:
                        basic_submissions.append({
                            "submission_id": submission["id"],
                            "title": submission["title"],
                            "slug": submission["titleSlug"],
                            "timestamp": submission["timestamp"],
                            "submission_time": datetime.fromtimestamp(int(submission["timestamp"])).strftime(
                                "%Y-%m-%d %H:%M:%S"
                            ),
                        })

                    return basic_submissions

        except Exception as e:
            logger.error(f"Error fetching submissions: {str(e)}", exc_info=True)
            return []


def html_to_text(html):
    """
    Convert HTML to formatted text.

    Args:
        html (str): HTML content

    Returns:
        str: Formatted text
    """

    def normalize_var_text(raw_text: str) -> str:
        cleaned = re.sub(r"\s*_\s*", "_", raw_text.strip())
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = re.sub(r"\s*,\s*", ",", cleaned)
        return cleaned

    def replace_latex_tokens(raw_text: str) -> str:
        command_patterns = [
            r"\\mathrm\s*\{([^{}]*)\}",
            r"\\text\s*\{([^{}]*)\}",
            r"\\mathbf\s*\{([^{}]*)\}",
            r"\\mathit\s*\{([^{}]*)\}",
            r"\\mathsf\s*\{([^{}]*)\}",
        ]
        for pattern in command_patterns:
            while True:
                updated = re.sub(pattern, r"\1", raw_text)
                if updated == raw_text:
                    break
                raw_text = updated
        replacements = [
            ("\\displaystyle", ""),
            ("\\leq", "<="),
            ("\\geq", ">="),
            ("\\le", "<="),
            ("\\ge", ">="),
            ("\\neq", "!="),
            ("\\times", "*"),
            ("\\cdot", "*"),
            ("\\ldots", "..."),
            ("\\cdots", "..."),
            ("\\dots", "..."),
            ("\\lvert", "|"),
            ("\\rvert", "|"),
            ("\\left", ""),
            ("\\right", ""),
            ("\\sum", "sum"),
            ("\\{", "{"),
            ("\\}", "}"),
            ("\\_", "_"),
        ]
        for token, replacement in replacements:
            raw_text = raw_text.replace(token, replacement)
        raw_text = re.sub(r"\\(?:mathrm|text|mathbf|mathit|mathsf)\s*", "", raw_text)
        raw_text = re.sub(r"\s*_\s*", "_", raw_text)
        raw_text = re.sub(r"\s*\^\s*", "^", raw_text)
        return raw_text

    def latex_to_plain(latex: str) -> str:
        text = replace_latex_tokens(latex)
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"_\{([^{}]+)\}", r"_\1", text)
        text = re.sub(r"\^\{([^{}]+)\}", r"^\1", text)
        text = text.replace("{", "").replace("}", "")
        return text.strip()

    def convert_latex_delimiters(raw_text: str, inline_strict: bool = False) -> str:
        def display_repl(match: re.Match) -> str:
            return latex_to_plain(match.group(1))

        raw_text = re.sub(r"\$\$\s*(.+?)\s*\$\$", display_repl, raw_text, flags=re.DOTALL)

        def inline_repl(match: re.Match) -> str:
            content = match.group(1)
            if not inline_strict and not re.search(r"[\\^_]", content):
                return match.group(0)
            return latex_to_plain(content)

        return re.sub(r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", inline_repl, raw_text)

    def is_probably_html(raw_text: str) -> bool:
        return bool(re.search(r"</?[a-z][^>]*>", raw_text))

    def extract_markdown_blocks(raw_text: str, pattern: str, token_prefix: str):
        blocks = []

        def repl(match: re.Match) -> str:
            blocks.append(match.group(0))
            return f"__{token_prefix}_{len(blocks) - 1}__"

        return re.sub(pattern, repl, raw_text, flags=re.DOTALL), blocks

    def restore_markdown_blocks(raw_text: str, blocks: list[str], token_prefix: str) -> str:
        for idx, block in enumerate(blocks):
            raw_text = raw_text.replace(f"__{token_prefix}_{idx}__", block)
        return raw_text

    def markdown_to_text(raw_text: str) -> str:
        text = normalize_math_delimiters(raw_text)
        text, fenced_blocks = extract_markdown_blocks(text, r"```[\s\S]*?```", "MD_CODE_BLOCK")
        text, inline_blocks = extract_markdown_blocks(text, r"`[^`]+`", "MD_INLINE_CODE")
        text = convert_latex_delimiters(text, inline_strict=True)
        text = replace_latex_tokens(text)
        text = restore_markdown_blocks(text, inline_blocks, "MD_INLINE_CODE")
        text = restore_markdown_blocks(text, fenced_blocks, "MD_CODE_BLOCK")
        lines = [line.rstrip() for line in text.splitlines()]
        text = "\n".join(lines)
        while "\n\n\n" in text:
            text = text.replace("\n\n\n", "\n\n")
        return text.strip()

    if not is_probably_html(html):
        return markdown_to_text(html)

    soup = BeautifulSoup(html, "html.parser")
    for sup in soup.find_all("sup"):
        sup.replace_with("^" + sup.get_text())
    for sub in soup.find_all("sub"):
        sub.replace_with("_" + sub.get_text())
    for var in soup.find_all("var"):
        var.replace_with(normalize_var_text(var.get_text()))
    for strong in soup.find_all("strong"):
        strong.replace_with(f"**{strong.get_text()}**")
    for em in soup.find_all("em"):
        em.replace_with(f"*{em.get_text()}*")
    for code in soup.find_all("code"):
        code.replace_with(f"`{code.get_text()}`")
    for li in soup.find_all("li"):
        li.insert_before("- ")
    for header in soup.find_all(["h2", "h3"]):
        header.replace_with(f"\n\n## {header.get_text(strip=True)}\n")
    for hr in soup.find_all("hr"):
        hr.replace_with("\n\n")
    for br in soup.find_all("br"):
        br.replace_with("\n")

    code_blocks = []
    for pre in soup.find_all("pre"):
        raw_lines = [line.rstrip() for line in pre.get_text().splitlines()]
        while raw_lines and not raw_lines[0].strip():
            raw_lines.pop(0)
        while raw_lines and not raw_lines[-1].strip():
            raw_lines.pop()
        indents = [len(line) - len(line.lstrip()) for line in raw_lines if line.strip()]
        min_indent = min(indents) if indents else 0
        content = "\n".join(line[min_indent:] for line in raw_lines)
        code_blocks.append(content)
        pre.replace_with(f"__CODE_BLOCK_{len(code_blocks) - 1}__")

    for p in soup.find_all("p"):
        p.insert_before("\n\n")

    text = soup.get_text()
    text = convert_latex_delimiters(text)
    text = replace_latex_tokens(text)

    for idx, content in enumerate(code_blocks):
        placeholder = f"__CODE_BLOCK_{idx}__"
        fenced = f"\n\n```\n{content}\n```\n"
        text = text.replace(placeholder, fenced)

    lines = [line.rstrip() for line in text.splitlines()]
    keywords = {"Example": 2, "Constraints": 2}
    for i, line in enumerate(lines):
        if line.startswith("#"):
            continue
        for keyword, level in keywords.items():
            if keyword in line:
                lines[i] = f"{'#' * level} {line}"
    text = "\n".join(line for line in lines)
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text.strip()
