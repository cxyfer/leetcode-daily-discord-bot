import discord
from discord import app_commands
from discord.ext import commands

from bot.api_client import ApiError, ApiNetworkError, ApiProcessingError, ApiRateLimitError
from bot.utils.logger import get_commands_logger
from bot.utils.ui_helpers import _get_locale, create_similar_results_message, send_api_error


class SimilarCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = get_commands_logger()

    @app_commands.command(name="similar", description=app_commands.locale_str("similar.description"))
    @app_commands.describe(
        query=app_commands.locale_str("similar.query"),
        problem=app_commands.locale_str("similar.problem"),
        top_k=app_commands.locale_str("similar.top_k"),
        source=app_commands.locale_str("similar.source"),
        public=app_commands.locale_str("similar.public"),
    )
    async def similar_command(
        self,
        interaction: discord.Interaction,
        query: str = None,
        problem: str = None,
        top_k: int = 5,
        source: str | None = None,
        public: bool = False,
    ):
        locale = _get_locale(self.bot, interaction)
        i18n = self.bot.i18n

        if not query and not problem:
            await interaction.response.send_message(
                i18n.t("errors.validation.no_query_provided", locale), ephemeral=not public
            )
            return

        cfg = self.bot.config.get_similar_config()
        top_k = max(1, min(top_k, 20))
        await interaction.response.defer(ephemeral=not public)

        try:
            if problem:
                if ":" in problem and not problem.startswith("http"):
                    src, pid = problem.split(":", 1)
                else:
                    resolved = await self.bot.api.resolve(problem)
                    if resolved and resolved.get("problem"):
                        problem_info = resolved["problem"]
                        src, pid = problem_info["source"], problem_info["id"]
                    elif resolved and resolved.get("source") and resolved.get("id"):
                        src, pid = resolved["source"], resolved["id"]
                    else:
                        src, pid = "leetcode", problem
                result = await self.bot.api.search_similar_by_id(src, pid, top_k, cfg.min_similarity)
            else:
                result = await self.bot.api.search_similar_by_text(query, source, top_k, cfg.min_similarity)

            if not result or not result.get("results"):
                not_found_msg = i18n.t("errors.validation.similar_not_found", locale)
                await interaction.followup.send(not_found_msg, ephemeral=not public)
                return

            if problem:
                embed, view = create_similar_results_message(
                    result, base_source=src, base_id=pid, bot=self.bot, locale=locale
                )
            else:
                embed, view = create_similar_results_message(result, bot=self.bot, locale=locale)

            await interaction.followup.send(embed=embed, view=view, ephemeral=not public)

        except ApiProcessingError:
            await send_api_error(interaction, "processing", self.bot, ephemeral=not public)
        except ApiNetworkError:
            await send_api_error(interaction, "network", self.bot, ephemeral=not public)
        except ApiRateLimitError:
            await send_api_error(interaction, "rate_limit", self.bot, ephemeral=not public)
        except ApiError as e:
            self.logger.error("/similar API error: %s", e)
            await send_api_error(interaction, "generic", self.bot, ephemeral=not public)
        except Exception as e:
            self.logger.error("/similar failed: %s", e, exc_info=True)
            await interaction.followup.send(i18n.t("daily.error", locale, error=e), ephemeral=not public)


async def setup(bot: commands.Bot):
    await bot.add_cog(SimilarCog(bot))
