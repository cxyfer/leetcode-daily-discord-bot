"""UI Helper Functions for Discord Bot

統一的 Discord UI 創建函數，包含所有 embed 和 view 的創建邏輯
"""

import asyncio
import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import discord
import pytz

from bot.api_client import ApiError, ApiNetworkError, ApiProcessingError, ApiRateLimitError
from bot.leetcode import generate_history_dates

from .ui_constants import (
    ATCODER_LOGO_URL,
    BUTTON_EMOJIS,
    DEFAULT_COLOR,
    DIFFICULTY_COLORS,
    DIFFICULTY_EMOJIS,
    DOMAIN_MAPPING,
    FIELD_EMOJIS,
    GEMINI_LOGO_URL,
    INSPIRATION_COLOR,
    INSPIRE_FIELDS,
    LEETCODE_LOGO_URL,
    LUOGU_DIFFICULTY_COLORS,
    LUOGU_DIFFICULTY_EMOJIS,
    MAX_BUTTON_CUSTOM_ID_LENGTH,
    MAX_BUTTON_LABEL_LENGTH,
    MAX_FIELD_LENGTH,
    MAX_PROBLEMS_PER_OVERVIEW,
    MAX_SIMILAR_QUESTIONS,
    MAX_SIMILAR_RESULT_DETAIL_BUTTONS,
    NON_DIFFICULTY_EMOJI,
    PROBLEMS_PER_FIELD,
)

# Module-level logger
logger = logging.getLogger("ui")


def get_user_color(user: discord.User) -> int:
    """根據使用者頭像URL產生顏色"""
    # 取得使用者頭像URL的hash值
    avatar_id = re.match(
        r"https://cdn\.discordapp\.com/avatars/\d+/(.*)\.png\?size=\d+",
        str(user.display_avatar.url),
    )
    if avatar_id:
        avatar_id = avatar_id.group(1)
    else:
        avatar_id = str(user.id)

    hash_value = hashlib.md5(avatar_id.encode()).hexdigest()
    # 取前6位作為顏色代碼
    color_hex = hash_value[:6]
    return int(color_hex, 16)


def get_difficulty_color(difficulty: str, source: str = "leetcode") -> int:
    """獲取難度對應的顏色"""
    if source == "luogu":
        normalized = difficulty.replace("\u2212", "-")
        return LUOGU_DIFFICULTY_COLORS.get(normalized, DEFAULT_COLOR)
    return DIFFICULTY_COLORS.get(difficulty, DEFAULT_COLOR)


def get_difficulty_emoji(difficulty: str) -> str:
    """獲取難度對應的表情符號"""
    return DIFFICULTY_EMOJIS.get(difficulty, NON_DIFFICULTY_EMOJI)


def get_source_difficulty_emoji(source: str, difficulty: str | None) -> str:
    """依題庫來源和難度取得對應表情符號"""
    if not difficulty:
        return NON_DIFFICULTY_EMOJI
    if source == "leetcode":
        return DIFFICULTY_EMOJIS.get(difficulty, NON_DIFFICULTY_EMOJI)
    if source == "luogu":
        normalized = difficulty.replace("\u2212", "-")
        return LUOGU_DIFFICULTY_EMOJIS.get(normalized, NON_DIFFICULTY_EMOJI)
    return NON_DIFFICULTY_EMOJI


def get_problem_emoji(problem_info: Dict[str, Any]) -> str:
    """依題目來源選擇對應表情符號"""
    source = problem_info.get("source", "leetcode")
    difficulty = problem_info.get("difficulty")
    return get_source_difficulty_emoji(source, difficulty)


def _normalize_similar_result_segment(value: Any, fallback: str) -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text or fallback


def _format_similarity(value: Any) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "?"


def _build_similar_result_line(index: int, result_item: Dict[str, Any]) -> str:
    source = _normalize_similar_result_segment(result_item.get("source"), "unknown")
    problem_id = _normalize_similar_result_segment(result_item.get("id"), "?")
    title = _normalize_similar_result_segment(result_item.get("title"), "Unknown problem")
    emoji = get_source_difficulty_emoji(source, result_item.get("difficulty"))
    separator = ". " if source == "leetcode" else ": "
    problem_text = f"{problem_id}{separator}{title}"
    link = result_item.get("link")
    if link:
        problem_text = f"[{problem_text}]({link})"
    return f"{index}. {emoji} {problem_text} [{source}] · {_format_similarity(result_item.get('similarity'))}"


def _build_similar_results_embed(
    result: Dict[str, Any],
    *,
    base_source: str | None = None,
    base_id: str | None = None,
) -> tuple[discord.Embed, bool]:
    embed = discord.Embed(title="🔍 相似題目", color=0x3498DB)

    if result.get("rewritten_query"):
        embed.add_field(name="✨ 重寫搜尋", value=result["rewritten_query"], inline=False)
    elif base_source and base_id:
        embed.add_field(name="🔗 基準題目", value=f"{base_source}:{base_id}", inline=False)

    lines = [_build_similar_result_line(index, item) for index, item in enumerate(result.get("results") or [], 1)]
    was_truncated = False

    for i in range(0, len(lines), PROBLEMS_PER_FIELD):
        chunk = lines[i : i + PROBLEMS_PER_FIELD]
        value = "\n".join(chunk)
        if len(value) > MAX_FIELD_LENGTH:
            value = value[: MAX_FIELD_LENGTH - 3] + "..."
            was_truncated = True
        field_name = f"{FIELD_EMOJIS['problems']} Results" if i == 0 else f"{FIELD_EMOJIS['problems']} Results (cont.)"
        embed.add_field(name=field_name, value=value, inline=False)

    return embed, was_truncated


def create_similar_results_embed(
    result: Dict[str, Any],
    *,
    base_source: str | None = None,
    base_id: str | None = None,
) -> discord.Embed:
    """建立相似題目搜尋結果 embed"""
    embed, _ = _build_similar_results_embed(result, base_source=base_source, base_id=base_id)
    return embed


def _is_safe_problem_button_segment(value: Any, *, max_length: int | None = None) -> bool:
    if value is None:
        return False
    text = str(value).strip()
    if not text or "|" in text:
        return False
    if max_length is not None and len(text) > max_length:
        return False
    return True


# Custom ID formats
PROBLEM_CUSTOM_ID_FMT = "problem|{source}|{pid}|{action}"


def _normalize_problem_button_segments(source: Any, problem_id: Any) -> tuple[str, str]:
    return str(source).strip(), str(problem_id).strip()


def _build_problem_custom_id(source: Any, problem_id: Any, action: str) -> str:
    """Safe builder that normalizes segments and formats the custom_id."""
    normalized_source, normalized_problem_id = _normalize_problem_button_segments(source, problem_id)
    return PROBLEM_CUSTOM_ID_FMT.format(
        source=normalized_source, pid=normalized_problem_id, action=action
    )


def _can_create_similar_result_view(results: List[Dict[str, Any]], *, was_truncated: bool) -> bool:
    return (
        bool(results)
        and not was_truncated
        and len(results) <= MAX_SIMILAR_RESULT_DETAIL_BUTTONS
        and all(
            _is_safe_problem_button_segment(item.get("source"))
            and _is_safe_problem_button_segment(item.get("id"), max_length=MAX_BUTTON_LABEL_LENGTH)
            and len(_build_problem_custom_id(item.get("source"), item.get("id"), "view"))
            <= MAX_BUTTON_CUSTOM_ID_LENGTH
            for item in results
        )
    )


def _create_similar_results_view(results: List[Dict[str, Any]]) -> discord.ui.View:
    view = discord.ui.View()
    for index, item in enumerate(results):
        # Normalize once for label, emoji, and custom_id
        source, pid = _normalize_problem_button_segments(item["source"], item["id"])
        emoji = get_source_difficulty_emoji(source, item.get("difficulty"))
        view.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.secondary,
                label=pid,
                emoji=emoji,
                custom_id=PROBLEM_CUSTOM_ID_FMT.format(source=source, pid=pid, action="view"),
                row=index // 5,
            )
        )
    return view


def create_similar_results_message(
    result: Dict[str, Any],
    *,
    base_source: str | None = None,
    base_id: str | None = None,
) -> tuple[discord.Embed, discord.ui.View | None]:
    embed, was_truncated = _build_similar_results_embed(result, base_source=base_source, base_id=base_id)
    results = result.get("results") or []
    view = (
        _create_similar_results_view(results)
        if _can_create_similar_result_view(results, was_truncated=was_truncated)
        else None
    )
    return embed, view


async def create_problem_embed(
    problem_info: Dict[str, Any],
    bot: Any,
    domain: str = "com",
    is_daily: bool = False,
    date_str: Optional[str] = None,
    user: Optional[discord.User] = None,
    title: Optional[str] = None,
    message: Optional[str] = None,
    history_problems: Optional[List[Dict[str, Any]]] = None,
) -> discord.Embed:
    """Create an embed for a LeetCode problem"""
    source = problem_info.get("source", "leetcode")
    if source != "leetcode":
        source_label = "AtCoder" if source == "atcoder" else source.capitalize()
        difficulty = problem_info.get("difficulty")
        title_emoji = get_source_difficulty_emoji(source, difficulty) if source == "luogu" else FIELD_EMOJIS["link"]
        embed_color = get_difficulty_color(difficulty, source) if difficulty else DEFAULT_COLOR
        embed = discord.Embed(
            title=f"{title_emoji} {problem_info['id']}: {problem_info['title']}",
            color=embed_color,
            url=problem_info.get("link"),
        )
        if (title or message) and user:
            embed.set_author(name=f"{user.display_name}", icon_url=user.display_avatar.url)
        if message:
            embed.description = message
        embed.add_field(name="Source", value=source_label, inline=False)
        if problem_info.get("difficulty"):
            embed.add_field(
                name=f"{FIELD_EMOJIS['difficulty']} Difficulty",
                value=f"**{problem_info['difficulty']}**",
                inline=True,
            )
        if problem_info.get("rating") and round(problem_info["rating"]) > 0:
            embed.add_field(
                name=f"{FIELD_EMOJIS['rating']} Rating",
                value=f"**{round(problem_info['rating'])}**",
                inline=True,
            )
        if problem_info.get("tags"):
            tags = problem_info["tags"]
            if isinstance(tags, str):
                try:
                    tags = json.loads(tags)
                except (json.JSONDecodeError, TypeError):
                    tags = [tags] if tags else []
            if tags:
                tags_str = ", ".join([f"||`{tag}`||" for tag in tags])
                embed.add_field(
                    name=f"{FIELD_EMOJIS['tags']} Tags",
                    value=tags_str,
                    inline=False,
                )
        footer_icon_url = ATCODER_LOGO_URL if source == "atcoder" else None
        if footer_icon_url:
            embed.set_footer(text=f"{source_label} Problem", icon_url=footer_icon_url)
        else:
            embed.set_footer(text=f"{source_label} Problem")
        return embed

    embed_color = get_difficulty_color(problem_info["difficulty"])

    embed = discord.Embed(
        title=f"{FIELD_EMOJIS['link']} {problem_info['id']}. {problem_info['title']}",
        color=embed_color,
        url=problem_info["link"],
    )

    # Only set author if title or message is provided
    if (title or message) and user:
        embed.set_author(name=f"{user.display_name}", icon_url=user.display_avatar.url)

    # Add alternative domain link
    domain_info = DOMAIN_MAPPING[domain]
    alt_link = problem_info["link"].replace(domain_info["full_name"], domain_info["alt_full_name"])
    embed.description = f"> Solve on [{domain_info['alt_name']} ({domain_info['alt_full_name']})]({alt_link})."

    if message:
        embed.description += f"\n{message}"

    # Add problem details
    embed.add_field(
        name=f"{FIELD_EMOJIS['difficulty']} Difficulty",
        value=f"**{problem_info['difficulty']}**",
        inline=True,
    )

    if problem_info.get("rating") and round(problem_info["rating"]) > 0:
        embed.add_field(
            name=f"{FIELD_EMOJIS['rating']} Rating",
            value=f"**{round(problem_info['rating'])}**",
            inline=True,
        )

    if problem_info.get("ac_rate"):
        embed.add_field(
            name=f"{FIELD_EMOJIS['ac_rate']} AC Rate",
            value=f"**{round(problem_info['ac_rate'], 2)}%**",
            inline=True,
        )

    if problem_info.get("tags"):
        tags_str = ", ".join([f"||`{tag}`||" for tag in problem_info["tags"]])
        embed.add_field(
            name=f"{FIELD_EMOJIS['tags']} Tags",
            value=tags_str if tags_str else "N/A",
            inline=False,
        )

    # Similar questions (use data directly from API response)
    if problem_info.get("similar_questions"):
        similar_q_list = []
        for sq in problem_info["similar_questions"][:MAX_SIMILAR_QUESTIONS]:
            if isinstance(sq, dict):
                sq_title = sq.get("title", "")
                sq_slug = sq.get("titleSlug") or sq.get("slug", "")
                sq_diff = sq.get("difficulty", "")
                emoji = get_difficulty_emoji(sq_diff)
                link = f"https://leetcode.com/problems/{sq_slug}/" if sq_slug else ""
                sq_text = f"- {emoji} [{sq_title}]({link})" if link else f"- {emoji} {sq_title}"
                similar_q_list.append(sq_text)
        if similar_q_list:
            embed.add_field(
                name=f"{FIELD_EMOJIS['similar']} Similar Questions",
                value="\n".join(similar_q_list),
                inline=False,
            )

    if history_problems:
        history_lines = []
        for item in history_problems[:5]:
            date_value = item.get("date", "")
            if not date_value:
                continue
            year = date_value.split("-")[0]
            emoji = get_difficulty_emoji(item.get("difficulty", ""))
            problem_id = item.get("id")
            problem_title = item.get("title")
            if not problem_id or not problem_title:
                continue
            link = item.get("link")
            problem_text = f"[{problem_id}. {problem_title}]({link})" if link else f"{problem_id}. {problem_title}"
            line = f"- [`{year}`] {emoji} {problem_text}"
            rating = item.get("rating")
            if rating is not None and round(rating) > 0:
                line += f" *{int(round(rating))}*"
            history_lines.append(line)
        if history_lines:
            embed.add_field(
                name=f"{FIELD_EMOJIS['history']} History Problems",
                value="\n".join(history_lines),
                inline=False,
            )

    # Set footer
    if is_daily:
        display_date = date_str or problem_info.get("date", "Today")
        embed.set_footer(
            text=f"LeetCode Daily Challenge | {display_date}",
            icon_url=LEETCODE_LOGO_URL,
        )
    else:
        embed.set_footer(text="LeetCode Problem", icon_url=LEETCODE_LOGO_URL)

    return embed


async def create_problem_view(problem_info: Dict[str, Any], bot: Any, domain: str = "com") -> discord.ui.View:
    """Create a view with buttons for a problem"""
    view = discord.ui.View()
    source = problem_info.get("source", "leetcode")
    pid = problem_info["id"]

    view.add_item(
        discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="題目描述",
            emoji=BUTTON_EMOJIS["description"],
            custom_id=_build_problem_custom_id(source, pid, "desc"),
        )
    )

    if bot.llm:
        view.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.success,
                label="LLM 翻譯",
                emoji=BUTTON_EMOJIS["translate"],
                custom_id=_build_problem_custom_id(source, pid, "translate"),
            )
        )

    if bot.llm_pro:
        view.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.danger,
                label="靈感啟發",
                emoji=BUTTON_EMOJIS["inspire"],
                custom_id=_build_problem_custom_id(source, pid, "inspire"),
            )
        )

    view.add_item(
        discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label="相似題目",
            emoji=BUTTON_EMOJIS["similar"],
            custom_id=_build_problem_custom_id(source, pid, "similar"),
        )
    )

    return view


def create_submission_embed(submission: Dict[str, Any], page: int, total: int, username: str) -> discord.Embed:
    """Create an embed for a user submission"""
    embed_color = get_difficulty_color(submission["difficulty"])

    embed = discord.Embed(
        title=f"{FIELD_EMOJIS['link']} {submission['id']}. {submission['title']}",
        color=embed_color,
        url=submission["link"],
    )

    # Add submission details
    embed.add_field(
        name=f"{FIELD_EMOJIS['difficulty']} Difficulty",
        value=f"**{submission['difficulty']}**",
        inline=True,
    )

    if submission.get("rating") and round(submission["rating"]) > 0:
        embed.add_field(
            name=f"{FIELD_EMOJIS['rating']} Rating",
            value=f"**{round(submission['rating'])}**",
            inline=True,
        )

    if submission.get("ac_rate"):
        embed.add_field(
            name=f"{FIELD_EMOJIS['ac_rate']} AC Rate",
            value=f"**{round(submission['ac_rate'], 2)}%**",
            inline=True,
        )

    if submission.get("tags"):
        tags_str = ", ".join([f"||`{tag}`||" for tag in submission["tags"]])
        embed.add_field(name=f"{FIELD_EMOJIS['tags']} Tags", value=tags_str, inline=False)

    embed.set_author(name=f"{username}'s Recent Submissions", icon_url=LEETCODE_LOGO_URL)
    embed.set_footer(text=f"Problem {page + 1} of {total}")

    return embed


def create_submission_view(
    submission: Dict[str, Any],
    bot: Any,
    current_page: int,
    username: str,
    total_submissions: Optional[int] = None,
) -> discord.ui.View:
    """Create a view for submission navigation"""
    view = discord.ui.View()
    show_nav = total_submissions is not None
    source = submission.get("source", "leetcode")
    pid = submission["id"]

    if show_nav and total_submissions:
        prev_button = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            emoji=BUTTON_EMOJIS["previous"],
            custom_id=f"user_sub_prev_{username}_{current_page}",
            disabled=(current_page <= 0),
            row=0,
        )
        view.add_item(prev_button)

    view.add_item(
        discord.ui.Button(
            style=discord.ButtonStyle.primary,
            emoji=BUTTON_EMOJIS["description"],
            custom_id=_build_problem_custom_id(source, pid, "desc"),
            row=0,
        )
    )

    if bot.llm:
        view.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.success,
                emoji=BUTTON_EMOJIS["translate"],
                custom_id=_build_problem_custom_id(source, pid, "translate"),
                row=0,
            )
        )

    if bot.llm_pro:
        view.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.danger,
                emoji=BUTTON_EMOJIS["inspire"],
                custom_id=_build_problem_custom_id(source, pid, "inspire"),
                row=0,
            )
        )

    if show_nav and total_submissions:
        next_button = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            emoji=BUTTON_EMOJIS["next"],
            custom_id=f"user_sub_next_{username}_{current_page}",
            disabled=(current_page >= total_submissions - 1),
            row=0,
        )
        view.add_item(next_button)

    return view


def create_problems_overview_embed(
    problems: List[Dict[str, Any]],
    domain: str,
    user: Optional[discord.User] = None,
    message: Optional[str] = None,
    title: Optional[str] = None,
    source_label: str = "LeetCode",
    show_instructions: bool = True,
    footer_icon_url: Optional[str] = LEETCODE_LOGO_URL,
) -> discord.Embed:
    """Create an overview embed showing all problems with basic info in user-provided order"""
    embed_title = title if title else f"{FIELD_EMOJIS['search']} {source_label} Problems ({len(problems)} found)"

    embed = discord.Embed(
        title=embed_title,
        color=get_user_color(user) if user else DEFAULT_COLOR,
        description=message,
    )

    # Only set author if title or message is provided
    if (title or message) and user:
        embed.set_author(name=f"{user.display_name}", icon_url=user.display_avatar.url)

    # Split problems into chunks
    for i in range(0, len(problems), PROBLEMS_PER_FIELD):
        chunk = problems[i : i + PROBLEMS_PER_FIELD]
        field_number = (i // PROBLEMS_PER_FIELD) + 1

        problem_lines = []
        for problem in chunk:
            emoji = get_problem_emoji(problem)
            source = problem.get("source", "leetcode")

            # Create line with hyperlink
            if source == "leetcode":
                line = f"- {emoji} **[{problem['id']}. {problem['title']}]({problem['link']})**"
            else:
                line = f"- {emoji} **[{problem['id']}: {problem['title']}]({problem['link']})**"
            if problem.get("rating") and problem["rating"] > 0:
                line += f" {FIELD_EMOJIS['rating']}{round(problem['rating'])}"

            problem_lines.append(line)

        # Determine field name
        if len(problems) <= PROBLEMS_PER_FIELD:
            field_name = f"{FIELD_EMOJIS['problems']} Problems"
        else:
            field_name = f"{FIELD_EMOJIS['problems']} Part {field_number}"

        embed.add_field(name=field_name, value="\n".join(problem_lines), inline=False)

    if show_instructions:
        embed.add_field(
            name=f"{FIELD_EMOJIS['instructions']} Instructions",
            value="Click the buttons below to view detailed information for each problem.",
            inline=False,
        )

    if footer_icon_url:
        embed.set_footer(
            text=f"{source_label} Problems Overview",
            icon_url=footer_icon_url,
        )
    else:
        embed.set_footer(text=f"{source_label} Problems Overview")
    embed.timestamp = datetime.now(timezone.utc)

    return embed


def create_problems_overview_view(problems: List[Dict[str, Any]], domain: str) -> discord.ui.View:
    """Create a view with buttons for each problem"""
    view = discord.ui.View()

    for i, problem in enumerate(problems[:MAX_PROBLEMS_PER_OVERVIEW]):
        emoji = get_problem_emoji(problem)
        source = problem.get("source", "leetcode")

        button = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label=f"{problem['id']}",
            emoji=emoji,
            custom_id=_build_problem_custom_id(source, problem["id"], "view"),
            row=i // 5,
        )
        view.add_item(button)

    return view


def create_settings_embed(
    guild_name: str,
    channel_mention: str,
    role_mention: str,
    post_time: str,
    timezone: str,
) -> discord.Embed:
    """Create an embed for server settings display"""
    embed = discord.Embed(title=f"{guild_name} 的 LeetCode 挑戰設定", color=DEFAULT_COLOR)

    embed.add_field(name="發送頻道", value=channel_mention, inline=False)
    embed.add_field(name="標記身分組", value=role_mention, inline=False)
    embed.add_field(name="發送時間", value=f"{post_time} ({timezone})", inline=False)

    return embed


def create_problem_description_embed(
    problem_info: Dict[str, Any], domain: str, source: str = "leetcode"
) -> discord.Embed:
    """Create an embed for problem description"""
    if source == "leetcode":
        emoji = get_difficulty_emoji(problem_info["difficulty"])
        embed_color = get_difficulty_color(problem_info["difficulty"], source)
        embed = discord.Embed(
            title=f"{emoji} {problem_info['id']}. {problem_info['title']}",
            description=problem_info["description"],
            color=embed_color,
            url=problem_info["link"],
        )
        embed.set_author(name="LeetCode Problem", icon_url=LEETCODE_LOGO_URL)
        return embed

    source_label = "AtCoder" if source == "atcoder" else source.capitalize()
    difficulty = problem_info.get("difficulty")
    emoji = get_source_difficulty_emoji(source, difficulty)
    embed_color = get_difficulty_color(difficulty, source) if difficulty else DEFAULT_COLOR
    embed = discord.Embed(
        title=f"{emoji} {problem_info['id']}: {problem_info['title']}",
        description=problem_info["description"],
        color=embed_color,
        url=problem_info["link"],
    )
    footer_icon_url = ATCODER_LOGO_URL if source == "atcoder" else None
    if footer_icon_url:
        embed.set_footer(text=f"{source_label} Problem", icon_url=footer_icon_url)
    else:
        embed.set_footer(text=f"{source_label} Problem")
    return embed


def create_inspiration_embed(inspiration_data: Dict[str, Any], problem_info: Dict[str, Any]) -> discord.Embed:
    """Create an embed for LLM inspiration"""
    embed = discord.Embed(title=f"{FIELD_EMOJIS['instructions']} 靈感啟發", color=INSPIRATION_COLOR)

    # Add inspiration content fields in fixed order
    for field_key in ["thinking", "traps", "algorithms", "inspiration"]:
        if field_key in inspiration_data and inspiration_data[field_key]:
            # Get the Chinese field name from mapping
            field_name = INSPIRE_FIELDS.get(field_key, field_key)
            content = inspiration_data[field_key]
            # Format content with proper spacing
            val_formatted = content.replace("\n\n", "\n").strip()
            embed.add_field(name=field_name, value=val_formatted, inline=False)

    # Set footer
    footer_text = inspiration_data.get("footer", f"Problem {problem_info['id']} 靈感啟發")
    embed.set_footer(text=footer_text, icon_url=GEMINI_LOGO_URL)

    return embed


async def _fetch_daily_history(bot: Any, domain: str, anchor_date: str) -> List[Dict[str, Any]]:
    """Fetch daily challenge history for the same day in previous years."""
    try:
        history_dates = generate_history_dates(anchor_date)
    except Exception:
        return []
    if not history_dates:
        return []

    sem = asyncio.Semaphore(5)

    async def fetch_one(d: str):
        async with sem:
            try:
                return await bot.api.get_daily(domain, d)
            except Exception:
                return None

    results = await asyncio.gather(*[fetch_one(d) for d in history_dates])
    return [r for r in results if r]


async def send_daily_challenge(
    bot: Any,
    channel_id: int = None,
    role_id: int = None,
    interaction: discord.Interaction = None,
    domain: str = "com",
    ephemeral: bool = True,
):
    """Fetches and sends the daily challenge via API."""
    try:
        logger.info("Attempting to send daily challenge. Domain: %s, Channel: %s", domain, channel_id)

        now_utc = datetime.now(pytz.UTC)
        date_str = now_utc.strftime("%Y-%m-%d")

        challenge_info = await bot.api.get_daily(domain)

        if not challenge_info:
            logger.error("No daily challenge for domain %s", domain)
            if interaction:
                await interaction.followup.send("找不到今日挑戰。", ephemeral=ephemeral)
            return None

        logger.info("Got daily challenge: %s. %s for domain %s", challenge_info["id"], challenge_info["title"], domain)

        history_anchor = challenge_info.get("date") or date_str
        history_problems = await _fetch_daily_history(bot, domain, history_anchor)

        embed = await create_problem_embed(
            problem_info=challenge_info,
            bot=bot,
            domain=domain,
            is_daily=True,
            history_problems=history_problems,
        )
        view = await create_problem_view(problem_info=challenge_info, bot=bot, domain=domain)

        if interaction:
            await interaction.followup.send(embed=embed, view=view, ephemeral=ephemeral)
        elif channel_id:
            target_channel = bot.get_channel(channel_id)
            if target_channel:
                content_msg = ""
                if role_id:
                    role = target_channel.guild.get_role(role_id)
                    if role:
                        content_msg = f"{role.mention}"
                    else:
                        logger.warning("Role ID %s not found in guild for channel %s", role_id, channel_id)
                await target_channel.send(
                    content=content_msg or None,
                    embed=embed,
                    view=view,
                )
                logger.info("Sent daily challenge to channel %s", channel_id)
            else:
                logger.error("Could not find channel %s", channel_id)
        else:
            logger.error("send_daily_challenge called without channel_id or interaction.")

        return challenge_info

    except (ApiProcessingError, ApiRateLimitError) as e:
        logger.warning("API error in send_daily_challenge: %s", e)
        if interaction:
            msg = "⏳ 資料準備中，請稍後重試。" if isinstance(e, ApiProcessingError) else "⏱️ 請求頻率過高，請稍後重試。"
            try:
                await interaction.followup.send(msg, ephemeral=ephemeral)
            except Exception:
                pass
            return None
        raise
    except (ApiNetworkError, ApiError) as e:
        logger.error("API error in send_daily_challenge: %s", e)
        if interaction:
            try:
                await interaction.followup.send("❌ 查詢失敗，請稍後重試。", ephemeral=ephemeral)
            except Exception:
                pass
        return None
    except Exception as e:
        logger.error("Error in send_daily_challenge: %s", e, exc_info=True)
        if interaction:
            try:
                await interaction.followup.send(f"發送每日挑戰時發生錯誤：{e}", ephemeral=ephemeral)
            except Exception:
                pass
        return None
