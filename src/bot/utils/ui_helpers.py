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
from bot.i18n import I18nService
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
    LEETCODE_LOGO_URL,
    LUOGU_DIFFICULTY_COLORS,
    LUOGU_DIFFICULTY_EMOJIS,
    MAX_BUTTON_CUSTOM_ID_LENGTH,
    MAX_BUTTON_LABEL_LENGTH,
    MAX_DAILY_SIMILAR_FIELD_LENGTH,
    MAX_FIELD_LENGTH,
    MAX_PROBLEMS_PER_OVERVIEW,
    MAX_SIMILAR_RESULT_DETAIL_BUTTONS,
    NON_DIFFICULTY_EMOJI,
    PROBLEMS_PER_FIELD,
)

# Module-level logger
logger = logging.getLogger("ui")


def _get_locale(bot: Any, interaction: discord.Interaction | None = None) -> str:
    """Resolve locale for the current context."""
    if not hasattr(bot, "i18n"):
        return "zh-TW"
    i18n: I18nService = bot.i18n
    guild_id = interaction.guild.id if interaction and interaction.guild else None
    guild_locale = str(interaction.guild_locale) if interaction and interaction.guild_locale else None
    interaction_locale = str(interaction.locale) if interaction else None
    config_default = getattr(bot.config, "default_locale", None) if hasattr(bot, "config") else None
    return i18n.resolve_locale(
        guild_id=guild_id,
        guild_locale=guild_locale,
        interaction_locale=interaction_locale,
        config_default=config_default,
    )


async def send_api_error(
    interaction: discord.Interaction,
    error_kind: str,
    bot: Any,
    *,
    ephemeral: bool = True,
) -> None:
    """Send a localized API error message.

    Args:
        interaction: The Discord interaction
        error_kind: One of 'processing', 'network', 'rate_limit', 'generic'
        bot: Bot instance with i18n service
        ephemeral: Whether the message should be ephemeral
    """
    locale = _get_locale(bot, interaction)
    i18n: I18nService = bot.i18n
    msg = i18n.t(f"errors.api.{error_kind}", locale)
    try:
        await interaction.followup.send(msg, ephemeral=ephemeral)
    except Exception:
        pass


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


def _format_problem_rating(value: Any) -> str | None:
    try:
        rating = round(float(value))
    except (TypeError, ValueError):
        return None
    return str(int(rating)) if rating > 0 else None


def _build_daily_similar_question_line(question: Dict[str, Any]) -> str | None:
    if not isinstance(question, dict):
        return None

    title = _normalize_similar_result_segment(question.get("title"), "")
    problem_id = _normalize_similar_result_segment(question.get("id"), "")
    difficulty = question.get("difficulty", "")
    emoji = get_difficulty_emoji(difficulty)

    if problem_id and title:
        display_text = f"{problem_id}. {title}"
    else:
        display_text = problem_id or title

    if not display_text:
        return None

    link = question.get("link")
    if not link:
        slug = question.get("titleSlug") or question.get("slug", "")
        if slug:
            link = f"https://leetcode.com/problems/{slug}/"

    line_text = f"[{display_text}]({link})" if link else display_text
    rating = _format_problem_rating(question.get("rating"))
    if rating:
        line_text += f" *{rating}*"

    return f"- {emoji} {line_text}"


def _join_lines_with_ellipsis(lines: List[str], *, max_length: int) -> tuple[str, int, bool]:
    if not lines:
        return "", 0, False

    rendered_lines: List[str] = []
    current_length = 0
    for line in lines:
        needed_length = len(line) + (1 if rendered_lines else 0)
        if current_length + needed_length <= max_length:
            rendered_lines.append(line)
            current_length += needed_length
            continue

        if not rendered_lines:
            return line[: max_length - 3] + "...", 1, True

        ellipsis_suffix = "\n..."
        joined = "\n".join(rendered_lines)
        if current_length + len(ellipsis_suffix) <= max_length:
            return joined + ellipsis_suffix, len(rendered_lines), True
        return joined[: max_length - 3] + "...", len(rendered_lines), True

    return "\n".join(rendered_lines), len(rendered_lines), False


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
    bot: Any = None,
    locale: str = "zh-TW",
) -> tuple[discord.Embed, bool]:
    i18n = bot.i18n if bot else None
    title = i18n.t("ui.embed.similar_title", locale) if i18n else "Similar Problems"
    embed = discord.Embed(title=title, color=0x3498DB)

    if result.get("rewritten_query"):
        field_name = i18n.t("ui.embed.rewritten_search", locale) if i18n else "Rewritten Search"
        embed.add_field(name=field_name, value=result["rewritten_query"], inline=False)
    elif base_source and base_id:
        field_name = i18n.t("ui.embed.base_problem", locale) if i18n else "Base Problem"
        embed.add_field(name=field_name, value=f"{base_source}:{base_id}", inline=False)

    lines = [_build_similar_result_line(index, item) for index, item in enumerate(result.get("results") or [], 1)]
    was_truncated = False

    for i in range(0, len(lines), PROBLEMS_PER_FIELD):
        chunk = lines[i : i + PROBLEMS_PER_FIELD]
        value = "\n".join(chunk)
        if len(value) > MAX_FIELD_LENGTH:
            value = value[: MAX_FIELD_LENGTH - 3] + "..."
            was_truncated = True
        results_label = i18n.t("ui.embed.results", locale) if i18n else "Results"
        problems_emoji = FIELD_EMOJIS["problems"]
        if i == 0:
            field_name = f"{problems_emoji} {results_label}"
        else:
            field_name = f"{problems_emoji} {results_label} (cont.)"
        embed.add_field(name=field_name, value=value, inline=False)

    return embed, was_truncated


def create_similar_results_embed(
    result: Dict[str, Any],
    *,
    base_source: str | None = None,
    base_id: str | None = None,
    bot: Any = None,
    locale: str = "zh-TW",
) -> discord.Embed:
    """建立相似題目搜尋結果 embed"""
    embed, _ = _build_similar_results_embed(result, base_source=base_source, base_id=base_id, bot=bot, locale=locale)
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
    return PROBLEM_CUSTOM_ID_FMT.format(source=normalized_source, pid=normalized_problem_id, action=action)


def _can_create_similar_result_view(results: List[Dict[str, Any]], *, was_truncated: bool) -> bool:
    return (
        bool(results)
        and not was_truncated
        and len(results) <= MAX_SIMILAR_RESULT_DETAIL_BUTTONS
        and all(
            _is_safe_problem_button_segment(item.get("source"))
            and _is_safe_problem_button_segment(item.get("id"), max_length=MAX_BUTTON_LABEL_LENGTH)
            and len(_build_problem_custom_id(item.get("source"), item.get("id"), "view")) <= MAX_BUTTON_CUSTOM_ID_LENGTH
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
    bot: Any = None,
    locale: str = "zh-TW",
) -> tuple[discord.Embed, discord.ui.View | None]:
    embed, was_truncated = _build_similar_results_embed(
        result, base_source=base_source, base_id=base_id, bot=bot, locale=locale
    )
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
    locale: str = "zh-TW",
) -> discord.Embed:
    """Create an embed for a LeetCode problem"""
    i18n = bot.i18n
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
        embed.add_field(name=i18n.t("ui.embed.source", locale), value=source_label, inline=False)
        if problem_info.get("difficulty"):
            embed.add_field(
                name=f"{FIELD_EMOJIS['difficulty']} {i18n.t('ui.embed.difficulty', locale)}",
                value=f"**{problem_info['difficulty']}**",
                inline=True,
            )
        if problem_info.get("rating") and round(problem_info["rating"]) > 0:
            embed.add_field(
                name=f"{FIELD_EMOJIS['rating']} {i18n.t('ui.embed.rating', locale)}",
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
                    name=f"{FIELD_EMOJIS['tags']} {i18n.t('ui.embed.tags', locale)}",
                    value=tags_str,
                    inline=False,
                )
        footer_icon_url = ATCODER_LOGO_URL if source == "atcoder" else None
        if footer_icon_url:
            embed.set_footer(text=i18n.t("ui.embed.atcoder_problem", locale), icon_url=footer_icon_url)
        else:
            embed.set_footer(text=i18n.t("ui.embed.description_author", locale))
        return embed

    embed_color = get_difficulty_color(problem_info["difficulty"])

    embed = discord.Embed(
        title=f"{FIELD_EMOJIS['link']} {problem_info['id']}. {problem_info['title']}",
        color=embed_color,
        url=problem_info["link"],
    )

    if (title or message) and user:
        embed.set_author(name=f"{user.display_name}", icon_url=user.display_avatar.url)

    domain_info = DOMAIN_MAPPING[domain]
    alt_link = problem_info["link"].replace(domain_info["full_name"], domain_info["alt_full_name"])
    embed.description = i18n.t(
        "ui.embed.solve_on",
        locale,
        alt_name=domain_info["alt_name"],
        alt_full_name=domain_info["alt_full_name"],
        link=alt_link,
    )

    if message:
        embed.description += f"\n{message}"

    embed.add_field(
        name=f"{FIELD_EMOJIS['difficulty']} {i18n.t('ui.embed.difficulty', locale)}",
        value=f"**{problem_info['difficulty']}**",
        inline=True,
    )

    if problem_info.get("rating") and round(problem_info["rating"]) > 0:
        embed.add_field(
            name=f"{FIELD_EMOJIS['rating']} {i18n.t('ui.embed.rating', locale)}",
            value=f"**{round(problem_info['rating'])}**",
            inline=True,
        )

    if problem_info.get("ac_rate"):
        embed.add_field(
            name=f"{FIELD_EMOJIS['ac_rate']} {i18n.t('ui.embed.ac_rate', locale)}",
            value=f"**{round(problem_info['ac_rate'], 2)}%**",
            inline=True,
        )

    if problem_info.get("tags"):
        tags_str = ", ".join([f"||`{tag}`||" for tag in problem_info["tags"]])
        embed.add_field(
            name=f"{FIELD_EMOJIS['tags']} {i18n.t('ui.embed.tags', locale)}",
            value=tags_str if tags_str else "N/A",
            inline=False,
        )

    if problem_info.get("similar_questions"):
        similar_q_list = []
        for sq in problem_info["similar_questions"]:
            line = _build_daily_similar_question_line(sq)
            if line:
                similar_q_list.append(line)
        if similar_q_list:
            similar_value, rendered_count, was_truncated = _join_lines_with_ellipsis(
                similar_q_list, max_length=MAX_DAILY_SIMILAR_FIELD_LENGTH
            )
            count_suffix = "+" if was_truncated else ""
            embed.add_field(
                name=i18n.t("ui.embed.similar_questions", locale, count=rendered_count, suffix=count_suffix),
                value=similar_value,
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
                name=f"{FIELD_EMOJIS['history']} {i18n.t('ui.embed.history_problems', locale)}",
                value="\n".join(history_lines),
                inline=False,
            )

    if is_daily:
        display_date = date_str or problem_info.get("date", "Today")
        embed.set_footer(
            text=i18n.t("ui.embed.daily_footer", locale, date=display_date),
            icon_url=LEETCODE_LOGO_URL,
        )
    else:
        embed.set_footer(text=i18n.t("ui.embed.problem_footer", locale), icon_url=LEETCODE_LOGO_URL)

    return embed


async def create_problem_view(
    problem_info: Dict[str, Any], bot: Any, domain: str = "com", locale: str = "zh-TW"
) -> discord.ui.View:
    """Create a view with buttons for a problem"""
    i18n = bot.i18n
    view = discord.ui.View()
    source = problem_info.get("source", "leetcode")
    pid = problem_info["id"]

    view.add_item(
        discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label=i18n.t("ui.buttons.description", locale),
            emoji=BUTTON_EMOJIS["description"],
            custom_id=_build_problem_custom_id(source, pid, "desc"),
        )
    )

    if bot.llm:
        view.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.success,
                label=i18n.t("ui.buttons.translate", locale),
                emoji=BUTTON_EMOJIS["translate"],
                custom_id=_build_problem_custom_id(source, pid, "translate"),
            )
        )

    if bot.llm_pro:
        view.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.danger,
                label=i18n.t("ui.buttons.inspire", locale),
                emoji=BUTTON_EMOJIS["inspire"],
                custom_id=_build_problem_custom_id(source, pid, "inspire"),
            )
        )

    view.add_item(
        discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label=i18n.t("ui.buttons.similar", locale),
            emoji=BUTTON_EMOJIS["similar"],
            custom_id=_build_problem_custom_id(source, pid, "similar"),
        )
    )

    return view


def create_submission_embed(
    submission: Dict[str, Any], page: int, total: int, username: str, bot: Any = None, locale: str = "zh-TW"
) -> discord.Embed:
    """Create an embed for a user submission"""
    i18n = bot.i18n if bot else None
    embed_color = get_difficulty_color(submission["difficulty"])

    embed = discord.Embed(
        title=f"{FIELD_EMOJIS['link']} {submission['id']}. {submission['title']}",
        color=embed_color,
        url=submission["link"],
    )

    embed.add_field(
        name=f"{FIELD_EMOJIS['difficulty']} {i18n.t('ui.embed.difficulty', locale) if i18n else 'Difficulty'}",
        value=f"**{submission['difficulty']}**",
        inline=True,
    )

    if submission.get("rating") and round(submission["rating"]) > 0:
        embed.add_field(
            name=f"{FIELD_EMOJIS['rating']} {i18n.t('ui.embed.rating', locale) if i18n else 'Rating'}",
            value=f"**{round(submission['rating'])}**",
            inline=True,
        )

    if submission.get("ac_rate"):
        embed.add_field(
            name=f"{FIELD_EMOJIS['ac_rate']} {i18n.t('ui.embed.ac_rate', locale) if i18n else 'AC Rate'}",
            value=f"**{round(submission['ac_rate'], 2)}%**",
            inline=True,
        )

    if submission.get("tags"):
        tags_str = ", ".join([f"||`{tag}`||" for tag in submission["tags"]])
        embed.add_field(
            name=f"{FIELD_EMOJIS['tags']} {i18n.t('ui.embed.tags', locale) if i18n else 'Tags'}",
            value=tags_str,
            inline=False,
        )

    author_name = (
        i18n.t("ui.embed.submission_author", locale, username=username) if i18n else f"{username}'s Recent Submissions"
    )
    embed.set_author(name=author_name, icon_url=LEETCODE_LOGO_URL)
    footer_text = (
        i18n.t("ui.embed.submission_footer", locale, current=page + 1, total=total)
        if i18n
        else f"Problem {page + 1} of {total}"
    )
    embed.set_footer(text=footer_text)

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
    bot: Any = None,
    locale: str = "zh-TW",
) -> discord.Embed:
    """Create an overview embed showing all problems with basic info in user-provided order"""
    i18n = bot.i18n if bot else None
    if title:
        embed_title = title
    elif i18n:
        embed_title = i18n.t("ui.embed.problems_found", locale, source_label=source_label, count=len(problems))
    else:
        embed_title = f"{FIELD_EMOJIS['search']} {source_label} Problems ({len(problems)} found)"

    embed = discord.Embed(
        title=embed_title,
        color=get_user_color(user) if user else DEFAULT_COLOR,
        description=message,
    )

    if (title or message) and user:
        embed.set_author(name=f"{user.display_name}", icon_url=user.display_avatar.url)

    for i in range(0, len(problems), PROBLEMS_PER_FIELD):
        chunk = problems[i : i + PROBLEMS_PER_FIELD]
        field_number = (i // PROBLEMS_PER_FIELD) + 1

        problem_lines = []
        for problem in chunk:
            emoji = get_problem_emoji(problem)
            source = problem.get("source", "leetcode")

            if source == "leetcode":
                line = f"- {emoji} **[{problem['id']}. {problem['title']}]({problem['link']})**"
            else:
                line = f"- {emoji} **[{problem['id']}: {problem['title']}]({problem['link']})**"
            if problem.get("rating") and problem["rating"] > 0:
                line += f" {FIELD_EMOJIS['rating']}{round(problem['rating'])}"

            problem_lines.append(line)

        problems_emoji = FIELD_EMOJIS["problems"]
        if len(problems) <= PROBLEMS_PER_FIELD:
            problems_label = i18n.t("ui.embed.problems", locale) if i18n else "Problems"
            field_name = f"{problems_emoji} {problems_label}"
        else:
            part_label = (
                i18n.t("ui.embed.problems_part", locale, number=field_number) if i18n else f"Part {field_number}"
            )
            field_name = f"{problems_emoji} {part_label}"

        embed.add_field(name=field_name, value="\n".join(problem_lines), inline=False)

    if show_instructions:
        instructions_emoji = FIELD_EMOJIS["instructions"]
        instructions_label = i18n.t("ui.embed.instructions", locale) if i18n else "Instructions"
        instructions_text = (
            i18n.t("ui.embed.instructions_text", locale)
            if i18n
            else "Click the buttons below to view detailed information for each problem."
        )
        embed.add_field(
            name=f"{instructions_emoji} {instructions_label}",
            value=instructions_text,
            inline=False,
        )

    footer_text = (
        i18n.t("ui.embed.problems_overview", locale, source_label=source_label)
        if i18n
        else f"{source_label} Problems Overview"
    )
    if footer_icon_url:
        embed.set_footer(text=footer_text, icon_url=footer_icon_url)
    else:
        embed.set_footer(text=footer_text)
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
    language: str = "zh-TW",
    bot: Any = None,
    locale: str = "zh-TW",
) -> discord.Embed:
    """Create an embed for server settings display"""
    i18n = bot.i18n if bot else None
    title = i18n.t("ui.settings.title", locale, guild_name=guild_name) if i18n else f"{guild_name} Settings"
    embed = discord.Embed(title=title, color=DEFAULT_COLOR)

    channel_label = i18n.t("ui.settings.channel", locale) if i18n else "Channel"
    role_label = i18n.t("ui.settings.role", locale) if i18n else "Role"
    time_label = i18n.t("ui.settings.time", locale) if i18n else "Post Time"
    language_label = i18n.t("ui.settings.language", locale) if i18n else "Language"

    embed.add_field(name=channel_label, value=channel_mention, inline=False)
    embed.add_field(name=role_label, value=role_mention, inline=False)
    embed.add_field(name=time_label, value=f"{post_time} ({timezone})", inline=False)

    language_display = i18n.t(f"locale.{language}", locale) if i18n else language
    embed.add_field(name=language_label, value=language_display, inline=False)

    return embed


def create_problem_description_embed(
    problem_info: Dict[str, Any], domain: str, source: str = "leetcode", bot: Any = None, locale: str = "zh-TW"
) -> discord.Embed:
    """Create an embed for problem description"""
    i18n = bot.i18n if bot else None
    if source == "leetcode":
        emoji = get_difficulty_emoji(problem_info["difficulty"])
        embed_color = get_difficulty_color(problem_info["difficulty"], source)
        embed = discord.Embed(
            title=f"{emoji} {problem_info['id']}. {problem_info['title']}",
            description=problem_info["description"],
            color=embed_color,
            url=problem_info["link"],
        )
        author_label = i18n.t("ui.embed.description_author", locale) if i18n else "LeetCode Problem"
        embed.set_author(name=author_label, icon_url=LEETCODE_LOGO_URL)
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
    footer_text = (
        i18n.t("ui.embed.atcoder_problem", locale) if i18n and source == "atcoder" else f"{source_label} Problem"
    )
    if footer_icon_url:
        embed.set_footer(text=footer_text, icon_url=footer_icon_url)
    else:
        embed.set_footer(text=footer_text)
    return embed


def create_inspiration_embed(
    inspiration_data: Dict[str, Any], problem_info: Dict[str, Any], bot: Any = None, locale: str = "zh-TW"
) -> discord.Embed:
    """Create an embed for LLM inspiration"""
    i18n = bot.i18n if bot else None
    title = i18n.t("ui.inspire.title", locale) if i18n else "Inspiration"
    embed = discord.Embed(title=title, color=INSPIRATION_COLOR)

    field_keys = ["thinking", "traps", "algorithms", "inspiration"]
    for field_key in field_keys:
        if field_key in inspiration_data and inspiration_data[field_key]:
            field_name = i18n.t(f"ui.inspire.{field_key}", locale) if i18n else field_key.capitalize()
            content = inspiration_data[field_key]
            val_formatted = content.replace("\n\n", "\n").strip()
            embed.add_field(name=field_name, value=val_formatted, inline=False)

    footer_text = inspiration_data.get("footer")
    if not footer_text:
        footer_text = (
            i18n.t("ui.inspire.default_footer", locale, id=problem_info["id"])
            if i18n
            else f"Problem {problem_info['id']} Inspiration"
        )
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
    guild_locale: str = None,
):
    """Fetches and sends the daily challenge via API."""
    if interaction:
        locale = _get_locale(bot, interaction)
    elif guild_locale:
        locale = guild_locale
    else:
        locale = getattr(bot.config, "default_locale", None) or "zh-TW"
    i18n = bot.i18n

    try:
        logger.info("Attempting to send daily challenge. Domain: %s, Channel: %s", domain, channel_id)

        now_utc = datetime.now(pytz.UTC)
        date_str = now_utc.strftime("%Y-%m-%d")

        challenge_info = await bot.api.get_daily(domain)

        if not challenge_info:
            logger.error("No daily challenge for domain %s", domain)
            if interaction:
                await interaction.followup.send(i18n.t("ui.embed.not_found", locale), ephemeral=ephemeral)
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
            locale=locale,
        )
        view = await create_problem_view(problem_info=challenge_info, bot=bot, domain=domain, locale=locale)

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
            error_kind = "processing" if isinstance(e, ApiProcessingError) else "rate_limit"
            await send_api_error(interaction, error_kind, bot, ephemeral=ephemeral)
            return None
        raise
    except (ApiNetworkError, ApiError) as e:
        logger.error("API error in send_daily_challenge: %s", e)
        if interaction:
            await send_api_error(interaction, "generic", bot, ephemeral=ephemeral)
        return None
    except Exception as e:
        logger.error("Error in send_daily_challenge: %s", e, exc_info=True)
        if interaction:
            try:
                await interaction.followup.send(i18n.t("daily.error", locale, error=e), ephemeral=ephemeral)
            except Exception:
                pass
        return None
