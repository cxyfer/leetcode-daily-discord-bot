from __future__ import annotations

import logging

import discord
from discord import app_commands

from .service import I18nService

logger = logging.getLogger("i18n.translator")


class BotTranslator(app_commands.Translator):
    def __init__(self, i18n: I18nService):
        super().__init__()
        self._i18n = i18n

    async def translate(
        self,
        string: app_commands.locale_str,
        locale: discord.Locale,
        context: app_commands.TranslationContext,
    ) -> str | None:
        key = string.message
        locale_str = str(locale)

        return self._i18n.maybe_t(f"commands.{key}", locale_str)
