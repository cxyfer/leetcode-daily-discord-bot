import discord
from discord import app_commands
from discord.ext import commands

from bot.api_client import ApiError, ApiNetworkError, ApiProcessingError, ApiRateLimitError
from bot.utils.logger import get_commands_logger
from bot.utils.ui_helpers import create_similar_results_embed


class SimilarCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = get_commands_logger()

    @app_commands.command(name="similar", description="搜尋相似題目")
    @app_commands.describe(
        query="題目敘述或關鍵字 (若指定 problem 則此欄位可略過)",
        problem="既有題目編號或網址 (例如: 1, atcoder:abc100_a)",
        top_k="返回結果數量 (預設 5)",
        source="題庫來源 (留空為全部)",
        public="是否公開顯示回覆 (預設為私密回覆)",
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
        if not query and not problem:
            await interaction.response.send_message(
                "請至少輸入題目敘述 (query) 或題目編號 (problem)", ephemeral=not public
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
                    if resolved:
                        src, pid = resolved["source"], resolved["id"]
                    else:
                        src, pid = "leetcode", problem
                result = await self.bot.api.search_similar_by_id(src, pid, top_k, cfg.min_similarity)
            else:
                result = await self.bot.api.search_similar_by_text(query, source, top_k, cfg.min_similarity)

            if not result or not result.get("results"):
                await interaction.followup.send("找不到相似題目。", ephemeral=not public)
                return

            if problem:
                embed = create_similar_results_embed(result, base_source=src, base_id=pid)
            else:
                embed = create_similar_results_embed(result)

            await interaction.followup.send(embed=embed, ephemeral=not public)

        except ApiProcessingError:
            await interaction.followup.send("⏳ 資料準備中，請稍後重試。", ephemeral=not public)
        except ApiNetworkError:
            await interaction.followup.send("🔌 API 連線失敗，請稍後重試。", ephemeral=not public)
        except ApiRateLimitError:
            await interaction.followup.send("⏱️ 請求頻率過高，請稍後重試。", ephemeral=not public)
        except ApiError as e:
            self.logger.error("/similar API error: %s", e)
            await interaction.followup.send("❌ 查詢失敗，請稍後重試。", ephemeral=not public)
        except Exception as e:
            self.logger.error("/similar failed: %s", e, exc_info=True)
            await interaction.followup.send("搜尋服務暫時不可用，請稍後再試", ephemeral=not public)


async def setup(bot: commands.Bot):
    await bot.add_cog(SimilarCog(bot))
