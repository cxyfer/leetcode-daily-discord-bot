"""UI Helper Functions for Discord Bot

統一的 Discord UI 創建函數，包含所有 embed 和 view 的創建邏輯
"""

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import discord
import pytz

from .logger import get_ui_logger
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
    MAX_PROBLEMS_PER_OVERVIEW,
    MAX_SIMILAR_QUESTIONS,
    NON_DIFFICULTY_EMOJI,
    PROBLEMS_PER_FIELD,
)

# Module-level logger
logger = get_ui_logger()


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


def get_difficulty_color(difficulty: str) -> int:
    """獲取難度對應的顏色"""
    return DIFFICULTY_COLORS.get(difficulty, DEFAULT_COLOR)


def get_difficulty_emoji(difficulty: str) -> str:
    """獲取難度對應的表情符號"""
    return DIFFICULTY_EMOJIS.get(difficulty, "⚫")


def get_problem_emoji(problem_info: Dict[str, Any]) -> str:
    """依題目來源選擇對應表情符號"""
    if problem_info.get("source", "leetcode") == "leetcode":
        return get_difficulty_emoji(problem_info.get("difficulty", ""))
    return NON_DIFFICULTY_EMOJI


async def create_problem_embed(
    problem_info: Dict[str, Any],
    bot: Any,
    domain: str = "com",
    is_daily: bool = False,
    date_str: Optional[str] = None,
    user: Optional[discord.User] = None,
    title: Optional[str] = None,
    message: Optional[str] = None,
) -> discord.Embed:
    """Create an embed for a LeetCode problem"""
    source = problem_info.get("source", "leetcode")
    if source != "leetcode":
        source_label = "AtCoder" if source == "atcoder" else source.capitalize()
        embed = discord.Embed(
            title=f"{FIELD_EMOJIS['link']} {problem_info['id']}: {problem_info['title']}",
            color=DEFAULT_COLOR,
            url=problem_info.get("link"),
        )
        if (title or message) and user:
            embed.set_author(name=f"{user.display_name}", icon_url=user.display_avatar.url)
        if message:
            embed.description = message
        embed.add_field(name="Source", value=source_label, inline=True)
        if problem_info.get("difficulty"):
            embed.add_field(
                name=f"{FIELD_EMOJIS['difficulty']} Difficulty",
                value=f"**{problem_info['difficulty']}**",
                inline=True,
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

    # Similar questions handling (limit to avoid too much processing)
    if problem_info.get("similar_questions"):
        current_client = bot.lcus if domain == "com" else bot.lccn
        similar_q_list = []
        for sq_slug_info in problem_info["similar_questions"][:MAX_SIMILAR_QUESTIONS]:
            sq_detail = await current_client.get_problem(slug=sq_slug_info["titleSlug"])
            if sq_detail:
                emoji = get_difficulty_emoji(sq_detail["difficulty"])
                sq_text = f"- {emoji} [{sq_detail['id']}. {sq_detail['title']}]({sq_detail['link']})"
                if sq_detail.get("rating") and sq_detail["rating"] > 0:
                    sq_text += f" *{int(sq_detail['rating'])}*"
                similar_q_list.append(sq_text)
        if similar_q_list:
            embed.add_field(
                name=f"{FIELD_EMOJIS['similar']} Similar Questions",
                value="\n".join(similar_q_list),
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
    view = discord.ui.View(timeout=None)
    source = problem_info.get("source", "leetcode")
    if source == "leetcode":
        description_prefix = getattr(bot, "LEETCODE_DISCRIPTION_BUTTON_PREFIX", "leetcode_problem_")
        translate_prefix = getattr(bot, "LEETCODE_TRANSLATE_BUTTON_PREFIX", "leetcode_translate_")
        inspire_prefix = getattr(bot, "LEETCODE_INSPIRE_BUTTON_PREFIX", "leetcode_inspire_")
        description_id = f"{description_prefix}{problem_info['id']}_{domain}"
        translate_id = f"{translate_prefix}{problem_info['id']}_{domain}"
        inspire_id = f"{inspire_prefix}{problem_info['id']}_{domain}"
    else:
        description_prefix = getattr(bot, "ATCODER_DESCRIPTION_BUTTON_PREFIX", "atcoder_problem|")
        translate_prefix = getattr(bot, "ATCODER_TRANSLATE_BUTTON_PREFIX", "atcoder_translate|")
        inspire_prefix = getattr(bot, "ATCODER_INSPIRE_BUTTON_PREFIX", "atcoder_inspire|")
        description_id = f"{description_prefix}{problem_info['id']}"
        translate_id = f"{translate_prefix}{problem_info['id']}"
        inspire_id = f"{inspire_prefix}{problem_info['id']}"

    # Description button
    view.add_item(
        discord.ui.Button(
            style=discord.ButtonStyle.primary,
            label="題目描述",
            emoji=BUTTON_EMOJIS["description"],
            custom_id=description_id,
        )
    )

    # LLM Translation button
    if bot.llm:
        view.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.success,
                label="LLM 翻譯",
                emoji=BUTTON_EMOJIS["translate"],
                custom_id=translate_id,
            )
        )

    # Inspiration button
    if bot.llm_pro:
        view.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.danger,
                label="靈感啟發",
                emoji=BUTTON_EMOJIS["inspire"],
                custom_id=inspire_id,
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
    view = discord.ui.View(timeout=None)
    show_nav = total_submissions is not None

    # Add previous button (leftmost)
    if show_nav and total_submissions:
        prev_button = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            emoji=BUTTON_EMOJIS["previous"],
            custom_id=f"user_sub_prev_{username}_{current_page}",
            disabled=(current_page <= 0),
            row=0,
        )
        view.add_item(prev_button)

    # Add description button
    view.add_item(
        discord.ui.Button(
            style=discord.ButtonStyle.primary,
            emoji=BUTTON_EMOJIS["description"],
            custom_id=f"{bot.LEETCODE_DISCRIPTION_BUTTON_PREFIX}{submission['id']}_com",
            row=0,
        )
    )

    # Add LLM buttons if available
    if bot.llm:
        view.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.success,
                emoji=BUTTON_EMOJIS["translate"],
                custom_id=f"{bot.LEETCODE_TRANSLATE_BUTTON_PREFIX}{submission['id']}_com",
                row=0,
            )
        )

    if bot.llm_pro:
        view.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.danger,
                emoji=BUTTON_EMOJIS["inspire"],
                custom_id=f"{bot.LEETCODE_INSPIRE_BUTTON_PREFIX}{submission['id']}_com",
                row=0,
            )
        )

    # Add next button (rightmost)
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
    view = discord.ui.View(timeout=None)

    # Create buttons for each problem (max 25 buttons per view)
    for i, problem in enumerate(problems[:MAX_PROBLEMS_PER_OVERVIEW]):
        emoji = get_problem_emoji(problem)
        source = problem.get("source", "leetcode")

        button = discord.ui.Button(
            style=discord.ButtonStyle.secondary,
            label=f"{problem['id']}",
            emoji=emoji,
            custom_id=f"problem_detail|{source}|{problem['id']}|{domain}",
            row=i // 5,  # 5 buttons per row
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
        embed_color = get_difficulty_color(problem_info["difficulty"])
        embed = discord.Embed(
            title=f"{emoji} {problem_info['id']}. {problem_info['title']}",
            description=problem_info["description"],
            color=embed_color,
            url=problem_info["link"],
        )
        embed.set_author(name="LeetCode Problem", icon_url=LEETCODE_LOGO_URL)
        return embed

    source_label = "AtCoder" if source == "atcoder" else source.capitalize()
    embed = discord.Embed(
        title=f"{NON_DIFFICULTY_EMOJI} {problem_info['id']}: {problem_info['title']}",
        description=problem_info["description"],
        color=DEFAULT_COLOR,
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


async def send_daily_challenge(
    bot: Any,
    channel_id: int = None,
    role_id: int = None,
    interaction: discord.Interaction = None,
    domain: str = "com",
    ephemeral: bool = True,
):
    """Fetches and sends the LeetCode daily challenge."""
    try:
        logger.info(
            f"Attempting to send daily challenge. Domain: {domain}, Channel: {channel_id}, "
            f"Interaction: {'Yes' if interaction else 'No'}"
        )

        current_client = bot.lcus if domain == "com" else bot.lccn

        # Determine date string based on LeetCode's server timezone for daily challenges
        now_utc = datetime.now(pytz.UTC)
        date_str = now_utc.strftime("%Y-%m-%d")

        logger.debug(f"Fetching daily challenge for date: {date_str} (UTC), domain: {domain}")
        challenge_info = await current_client.get_daily_challenge()

        if not challenge_info:
            logger.error(f"Failed to get daily challenge info for domain {domain}.")
            if interaction:
                await interaction.followup.send("Could not fetch daily challenge.", ephemeral=ephemeral)
            return None

        logger.info(f"Got daily challenge: {challenge_info['id']}. {challenge_info['title']} for domain {domain}")

        embed = await create_problem_embed(
            problem_info=challenge_info,
            bot=bot,
            domain=domain,
            is_daily=True,
        )
        view = await create_problem_view(problem_info=challenge_info, bot=bot, domain=domain)

        if interaction:
            # If called from a slash command
            await interaction.followup.send(embed=embed, view=view, ephemeral=ephemeral)
            logger.info(f"Sent daily challenge via interaction {interaction.id}")
        elif channel_id:
            target_channel = bot.get_channel(channel_id)
            if target_channel:
                content_msg = ""
                if role_id:
                    # Ensure role exists in guild before mentioning
                    guild = target_channel.guild
                    role = guild.get_role(role_id)
                    if role:
                        content_msg = f"{role.mention}"
                    else:
                        logger.warning(f"Role ID {role_id} not found in guild {guild.id} for channel {channel_id}.")
                await target_channel.send(
                    content=content_msg if content_msg else None,
                    embed=embed,
                    view=view,
                )
                logger.info(f"Sent daily challenge to channel {channel_id}")
            else:
                logger.error(f"Could not find channel {channel_id} to send daily challenge.")
        else:
            logger.error("send_daily_challenge called without channel_id or interaction.")

        return challenge_info

    except Exception as e:
        logger.error(f"Error in send_daily_challenge: {e}", exc_info=True)
        if interaction:
            try:
                await interaction.followup.send(
                    f"An error occurred while sending the daily challenge: {e}",
                    ephemeral=ephemeral,
                )
            except Exception:
                pass
        return None
