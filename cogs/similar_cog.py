# cogs/similar_cog.py
import discord
from discord import app_commands
from discord.ext import commands

from embeddings import (
    EmbeddingGenerator,
    EmbeddingRewriter,
    EmbeddingStorage,
    SimilaritySearcher,
)
from utils.config import get_config
from utils.database import EmbeddingDatabaseManager
from utils.logger import get_commands_logger
from utils.ui_constants import (
    DEFAULT_COLOR,
    FIELD_EMOJIS,
    LEETCODE_LOGO_URL,
    MAX_FIELD_LENGTH,
    NON_DIFFICULTY_EMOJI,
    PROBLEMS_PER_FIELD,
)
from utils.ui_helpers import get_difficulty_emoji
from utils.source_detector import looks_like_problem_id


class SimilarCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = get_commands_logger()
        self.config = get_config()
        self.similar_config = self.config.get_similar_config()
        self.embedding_config = self.config.get_embedding_model_config()

        self.db = EmbeddingDatabaseManager(db_path=self.config.database_path)
        self.db.create_vec_table(self.embedding_config.dim)
        if not self.db.check_dimension_consistency(self.embedding_config.dim):
            raise ValueError(
                f"Embedding dimension mismatch! Config: {self.embedding_config.dim}. Run --rebuild."
            )

        self.storage = EmbeddingStorage(self.db)
        self.rewriter = EmbeddingRewriter(self.config)
        self.generator = EmbeddingGenerator(self.config)
        self.searcher = SimilaritySearcher(self.db, self.storage)

    def cog_unload(self) -> None:
        try:
            self.db.close()
        except Exception as exc:
            self.logger.warning("Failed to close embedding DB: %s", exc)

    @app_commands.command(name="similar", description="搜尋相似題目")
    @app_commands.describe(
        query="題目敘述或關鍵字",
        top_k="返回結果數量 (預設 5)",
        source="題庫來源 (留空為全部)",
        public="是否公開顯示回覆 (預設為私密回覆)",
    )
    async def similar_command(
        self,
        interaction: discord.Interaction,
        query: str,
        top_k: int = 5,
        source: str | None = None,
        public: bool = False,
    ):
        if not query or not query.strip():
            await interaction.response.send_message(
                "請輸入題目描述或關鍵字", ephemeral=not public
            )
            return

        if looks_like_problem_id(query):
            await interaction.response.send_message(
                "請輸入題目描述或關鍵字，而非題目編號", ephemeral=not public
            )
            return

        top_k = max(1, min(top_k, 20))
        source_input = (source or "").strip().lower()
        source_filter = (
            None if not source_input or source_input == "all" else source_input
        )

        await interaction.response.defer(ephemeral=not public)

        try:
            total_vectors = await self.storage.count_embeddings(source_filter)
            if total_vectors == 0:
                await interaction.followup.send(
                    "尚未建立題庫索引，請聯繫管理員執行 `embedding_cli.py --build`",
                    ephemeral=not public,
                )
                return

            rewritten = await self.rewriter.rewrite(query)
            if not rewritten or not rewritten.strip():
                rewritten = query
            embedding = await self.generator.embed(rewritten)
            results = await self.searcher.search(
                embedding,
                source_filter,
                top_k,
                self.similar_config.min_similarity,
            )

            embed = await self.create_results_embed(query, rewritten, results, source_filter)
            await interaction.followup.send(embed=embed, ephemeral=not public)
        except Exception as exc:
            self.logger.error("/similar failed: %s", exc, exc_info=True)
            await interaction.followup.send(
                "搜尋服務暫時不可用，請稍後再試", ephemeral=not public
            )
            
    def _truncate_text(self, text: str, max_length: int = MAX_FIELD_LENGTH) -> str:
        """Helper to truncate text with ellipsis if it exceeds max_length."""
        suffix = "..."
        if len(text) <= max_length:
            return text
        return text[: max_length - len(suffix)] + suffix

    async def create_results_embed(
        self, query: str, rewritten_query: str, results: list, source: str | None
    ):
        display_source = source or "all"
        show_source = source is None
        title = f"{FIELD_EMOJIS['search']} 相似題目搜尋結果"
        embed = discord.Embed(title=title, color=DEFAULT_COLOR)
        
        # Truncate content to avoid Discord limits (1024 chars per field value)
        display_query = self._truncate_text(query)
        display_rewritten = self._truncate_text(rewritten_query)

        embed.add_field(name="❓ 原始查詢", value=display_query, inline=False)
        embed.add_field(name="🤖 AI 重寫", value=display_rewritten, inline=False)

        if not results:
            embed.add_field(
                name="🔍 搜尋結果",
                value="找不到相似題目，請嘗試更詳細的描述",
                inline=False,
            )
            return embed

        # Build result fields respecting both problem count and Discord's field length limit
        current_lines: list[str] = []
        current_length = 0  # total characters in "\n".join(current_lines)
        start_idx_for_field = 1

        for idx, result in enumerate(results, start=1):
            problem_id = result.get("problem_id")
            problem_title = result.get("title") or f"Problem {problem_id}"
            difficulty = result.get("difficulty") or "Unknown"
            emoji = (
                get_difficulty_emoji(difficulty) if result.get("difficulty") else NON_DIFFICULTY_EMOJI
            )
            similarity = result.get("similarity", 0)
            link = result.get("link") or ""
            
            source_tag = ""
            if show_source:
                source_tag = f"[{result.get('source', 'unknown')}]"
            
            source_fragment = f" {source_tag}" if source_tag else ""
            
            if link:
                line = f"{idx}. {emoji} [{problem_id}. {problem_title}]({link}){source_fragment} · {similarity:.2f}"
            else:
                line = f"{idx}. {emoji} {problem_id}. {problem_title}{source_fragment} · {similarity:.2f}"

            # Ensure an individual line never exceeds the field limit (minus safety margin)
            if len(line) > MAX_FIELD_LENGTH:
                line = self._truncate_text(line)

            # Determine if we need to start a new field before adding this line
            additional_length = len(line) + (1 if current_lines else 0)  # +1 for newline if not first line
            exceeds_length = current_length + additional_length > MAX_FIELD_LENGTH
            exceeds_count = len(current_lines) >= PROBLEMS_PER_FIELD

            if current_lines and (exceeds_length or exceeds_count):
                end_idx_for_field = idx - 1
                field_name = f"🔍 搜尋結果 ({start_idx_for_field}-{end_idx_for_field})"
                embed.add_field(
                    name=field_name,
                    value="\n".join(current_lines),
                    inline=False,
                )
                # Start a new field with the current line
                current_lines = [line]
                current_length = len(line)
                start_idx_for_field = idx
            else:
                current_lines.append(line)
                current_length += additional_length

        # Flush any remaining lines into a final field
        if current_lines:
            end_idx_for_field = len(results)
            field_name = f"🔍 搜尋結果 ({start_idx_for_field}-{end_idx_for_field})"
            embed.add_field(
                name=field_name,
                value="\n".join(current_lines),
                inline=False,
            )

        embed.set_footer(text=f"Source: {display_source}", icon_url=LEETCODE_LOGO_URL)
        return embed


async def setup(bot: commands.Bot):
    await bot.add_cog(SimilarCog(bot))