# cogs/interaction_handler_cog.py
import discord
from discord.ext import commands
import time
import asyncio
from leetcode import html_to_text # 確保這個 import 存在
# from utils.logger import get_logger # 使用 bot.logger

class InteractionHandlerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = bot.logger
        # 共享資源將透過 self.bot 存取, 例如:
        # self.lcus = bot.lcus
        # self.llm = bot.llm
        # self.LEETCODE_DISCRIPTION_BUTTON_PREFIX = bot.LEETCODE_DISCRIPTION_BUTTON_PREFIX
        
        # Cache for user submissions (to avoid re-fetching)
        self.submissions_cache = {}  # key: f"{username}_{user_id}", value: (submissions, timestamp, limit)
        
        # Track ongoing LLM requests to prevent duplicates
        self.ongoing_llm_requests = set()  # elements: (user_id, problem_id, request_type)
        self.ongoing_llm_requests_lock = asyncio.Lock()  # Lock for atomic operations

    async def _handle_duplicate_request(self, interaction: discord.Interaction, request_key: tuple, request_type: str) -> bool:
        """
        Check if a request is already in progress and handle the duplicate case.
        
        Args:
            interaction: Discord interaction object
            request_key: Tuple of (user_id, problem_id, request_type)
            request_type: Type of request ("translate" or "inspire")
            
        Returns:
            True if this is a duplicate request (already handled), False otherwise
        """
        async with self.ongoing_llm_requests_lock:
            if request_key in self.ongoing_llm_requests:
                if request_type == "translate":
                    message = "正在處理您的翻譯請求，請稍候..."
                else:
                    message = "正在處理您的靈感啟發請求，請稍候..."
                    
                await interaction.response.send_message(message, ephemeral=True)
                self.logger.info(f"防止重複{request_type}請求: user={interaction.user.name}, problem_id={request_key[1]}")
                return True
                
            # Add to ongoing requests
            self.ongoing_llm_requests.add(request_key)
            return False
    
    async def _cleanup_request(self, request_key: tuple) -> None:
        """
        Remove a request from the ongoing requests set.
        
        Args:
            request_key: Tuple of (user_id, problem_id, request_type)
        """
        async with self.ongoing_llm_requests_lock:
            self.ongoing_llm_requests.discard(request_key)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        # Ignore non-button interactions
        if interaction.type != discord.InteractionType.component:
            return

        custom_id = interaction.data.get("custom_id", "")

        # Button for displaying LeetCode problem description
        if custom_id.startswith(self.bot.LEETCODE_DISCRIPTION_BUTTON_PREFIX):
            self.logger.debug(f"接收到LeetCode按鈕交互: custom_id={custom_id}")
            
            try:
                parts = custom_id.split("_")
                problem_id = parts[2]
                domain = parts[3] if len(parts) > 3 else "com"
                
                self.logger.debug(f"嘗試獲取題目: problem_id={problem_id}, domain={domain}")
                
                client = self.bot.lcus if domain == "com" else self.bot.lccn
                
                if problem_id and problem_id.isdigit():
                    problem_info = await client.get_problem(problem_id=problem_id)
                    
                    if problem_info and problem_info.get("content"):
                        problem_content = html_to_text(problem_info["content"])
                        
                        if len(problem_content) > 1900:
                            problem_content = problem_content[:1900] + "...\n(內容已截斷，請前往 LeetCode 網站查看完整題目)"
                        
                        emoji = {'Easy': '🟢', 'Medium': '🟡', 'Hard': '🔴'}.get(problem_info['difficulty'], '')
                        problem_content = f"# {emoji} [{problem_info['id']}. {problem_info['title']}]({problem_info['link']}) ({problem_info['difficulty']})\n\n{problem_content}"
                        
                        self.logger.debug(f"成功獲取題目內容: length={len(problem_content)}")
                    else:
                        problem_content = "無法獲取題目描述，請前往 LeetCode 網站查看。"
                        self.logger.warning(f"題目沒有內容: problem_id={problem_id}")
                else:
                    problem_content = "無效的題目ID，無法顯示題目描述。"
                    self.logger.warning(f"無效的題目ID: {problem_id}")
                
                await interaction.response.send_message(problem_content, ephemeral=True)
                self.logger.info(f"成功發送題目描述給 @{interaction.user.name}: channel_id={interaction.channel.id}, problem_id={problem_id}, domain={domain}, content_length={len(problem_content)}")
                
            except discord.errors.InteractionResponded:
                await interaction.followup.send("已經回應過此交互，請重新點擊按鈕。", ephemeral=True)
            except Exception as e:
                self.logger.error(f"處理按鈕交互時發生錯誤: {e}", exc_info=True)
                try:
                    await interaction.response.send_message(f"顯示題目時發生錯誤：{str(e)}", ephemeral=True)
                except: # noqa
                    try:
                        await interaction.followup.send(f"顯示題目時發生錯誤：{str(e)}", ephemeral=True)
                    except: # noqa
                        pass

        # Button for LLM translation
        elif custom_id.startswith(self.bot.LEETCODE_TRANSLATE_BUTTON_PREFIX):
            self.logger.debug(f"接收到LeetCode LLM翻譯按鈕交互: custom_id={custom_id}")
            try:
                parts = custom_id.split("_")
                problem_id = parts[2]
                domain = parts[3] if len(parts) > 3 else "com"
                
                # Handle duplicate request prevention
                request_key = (interaction.user.id, problem_id, "translate")
                if await self._handle_duplicate_request(interaction, request_key, "translate"):
                    return
                
                await interaction.response.defer(ephemeral=True)

                self.logger.debug(f"嘗試獲取題目並進行LLM翻譯: problem_id={problem_id}, domain={domain}")

                client = self.bot.lcus if domain == "com" else self.bot.lccn

                if problem_id and problem_id.isdigit():
                    translation_data = self.bot.llm_translate_db.get_translation(int(problem_id), domain)
                    if translation_data:
                        self.logger.debug(f"從DB取得LLM翻譯: problem_id={problem_id}")
                        translation = translation_data["translation"]
                        model_name = translation_data.get("model_name", "Unknown Model")
                        
                        if translation and model_name:
                            footer_text = f"\n\n✨ 由 `{model_name}` 提供翻譯"
                            if len(translation) + len(footer_text) > 2000:
                                translation = translation[:2000-len(footer_text)]
                            translation += footer_text
                            
                        await interaction.followup.send(translation, ephemeral=True)
                        # Cleanup will be handled by finally block
                        return

                    problem_info = await client.get_problem(problem_id=problem_id)
                    if problem_info and problem_info.get("content"):
                        problem_content_raw = html_to_text(problem_info["content"])
                        try:
                            translation = await self.bot.llm.translate(problem_content_raw, "zh-TW")
                            model_name = getattr(self.bot.llm, "model_name", "Unknown Model")
                            
                            footer_text = f"\n\n✨ 由 `{model_name}` 提供翻譯"
                            max_length = 2000 - len(footer_text)
                            if len(translation) > max_length:
                                translation = translation[:max_length-10] + "...\n(翻譯內容已截斷)"
                                
                            self.bot.llm_translate_db.save_translation(int(problem_id), domain, translation, model_name)
                            translation += footer_text
                            
                            await interaction.followup.send(translation, ephemeral=True)
                            self.logger.info(f"成功發送LLM翻譯給 @{interaction.user.name}: channel_id={interaction.channel.id}, problem_id={problem_id}, domain={domain}, content_length={len(translation)}")
                        except Exception as llm_e:
                            self.logger.error(f"LLM 翻譯失敗: {llm_e}", exc_info=True)
                            await interaction.followup.send(f"LLM 翻譯失敗：{str(llm_e)}", ephemeral=True)
                    else:
                        self.logger.warning(f"題目沒有內容: problem_id={problem_id}")
                        await interaction.followup.send("無法獲取題目描述，請前往 LeetCode 網站查看。", ephemeral=True)
                else:
                    self.logger.warning(f"無效的題目ID: {problem_id}")
                    await interaction.followup.send("無效的題目ID，無法顯示翻譯。", ephemeral=True)
            except discord.errors.InteractionResponded:
                await interaction.followup.send("已經回應過此交互，請重新點擊按鈕。", ephemeral=True)
            except Exception as e:
                self.logger.error(f"處理LLM翻譯按鈕交互時發生錯誤: {e}", exc_info=True)
                try:
                    await interaction.followup.send(f"LLM 翻譯時發生錯誤：{str(e)}", ephemeral=True)
                except: # noqa
                    pass
            finally:
                # Remove from ongoing requests
                await self._cleanup_request(request_key)
        
        # Button for LLM inspire
        elif custom_id.startswith(self.bot.LEETCODE_INSPIRE_BUTTON_PREFIX):
            self.logger.debug(f"接收到LeetCode 靈感啟發按鈕交互: custom_id={custom_id}")
            
            INSPIRE_FIELDS = [ # 定義在方法內部或類別層級，如果多處使用
                ("thinking", "🧠 思路"),
                ("traps", "⚠️ 陷阱"),
                ("algorithms", "🛠️ 推薦演算法"),
                ("inspiration", "✨ 其他靈感"),
            ]

            def format_inspire_field(val): # 輔助函式可以定義在方法內部或作為靜態方法
                if isinstance(val, list):
                    return '\n'.join(f"- {x}" for x in val)
                return str(val)

            try:
                parts = custom_id.split("_")
                problem_id = parts[2]
                domain = parts[3] if len(parts) > 3 else "com"
                
                # Handle duplicate request prevention
                request_key = (interaction.user.id, problem_id, "inspire")
                if await self._handle_duplicate_request(interaction, request_key, "inspire"):
                    return
                
                await interaction.response.defer(ephemeral=True)

                self.logger.debug(f"嘗試獲取題目並進行LLM靈感啟發: problem_id={problem_id}, domain={domain}")

                if not problem_id or not problem_id.isdigit():
                    self.logger.warning(f"無效的題目ID: {problem_id}")
                    await interaction.followup.send("無效的題目ID，無法顯示靈感啟發。", ephemeral=True)
                    # Cleanup will be handled by finally block
                    return

                inspire_result_data = self.bot.llm_inspire_db.get_inspire(int(problem_id), domain)
                model_name = "Unknown Model" # Default model name

                if inspire_result_data:
                    self.logger.debug(f"Get inspire result from DB: problem_id={problem_id}")
                    model_name = inspire_result_data.get("model_name", "Unknown Model")
                    # 從DB讀取時，inspire_result_data 已經是包含 "thinking", "traps" 等鍵的字典
                    inspire_result_content = inspire_result_data 
                else:
                    client = self.bot.lcus if domain == "com" else self.bot.lccn
                    problem_info = await client.get_problem(problem_id=problem_id)
                    if not (problem_info and problem_info.get("content")):
                        self.logger.warning(f"題目沒有內容: problem_id={problem_id}")
                        await interaction.followup.send("無法獲取題目資訊。", ephemeral=True)
                        # Cleanup will be handled by finally block
                        return
                    
                    problem_content_raw = html_to_text(problem_info["content"])
                    tags = problem_info.get("tags", [])
                    difficulty = problem_info.get("difficulty", "")
                    
                    try:
                        llm_output = await self.bot.llm_pro.inspire(problem_content_raw, tags, difficulty)
                        model_name = getattr(self.bot.llm_pro, "model_name", "Unknown Model")
                        
                        if not isinstance(llm_output, dict) or not all(k in llm_output for k in ["thinking", "traps", "algorithms", "inspiration"]):
                            raw_response = llm_output.get("raw", str(llm_output))
                            if len(raw_response) > 1900:
                                raw_response = raw_response[:1900] + "...\n(內容已截斷)"
                            await interaction.followup.send(raw_response, ephemeral=True)
                            self.logger.debug(f"發送原始 LLM 靈感回覆: problem_id={problem_id}")
                            # Cleanup will be handled by finally block
                            return
                        
                        # llm_output 是符合預期格式的字典
                        inspire_result_content = llm_output
                        # --- DB cache: save inspire result ---
                        # 確保儲存到DB的也是格式化後的字串
                        db_thinking = format_inspire_field(inspire_result_content.get("thinking",""))
                        db_traps = format_inspire_field(inspire_result_content.get("traps",""))
                        db_algorithms = format_inspire_field(inspire_result_content.get("algorithms",""))
                        db_inspiration = format_inspire_field(inspire_result_content.get("inspiration",""))

                        self.bot.llm_inspire_db.save_inspire(
                            int(problem_id), domain,
                            db_thinking, db_traps, db_algorithms, db_inspiration,
                            model_name=model_name
                        )
                    except Exception as llm_e:
                        self.logger.error(f"LLM 靈感啟發失敗: {llm_e}", exc_info=True)
                        await interaction.followup.send(f"LLM 靈感啟發失敗：{str(llm_e)}", ephemeral=True)
                        # Cleanup will be handled by finally block
                        return
                
                embed = discord.Embed(title="💡 靈感啟發", color=0x8e44ad)
                total_len = 0
                for key, field_name in INSPIRE_FIELDS:
                    # 從 inspire_result_content (可能是從DB來或LLM來) 取值並格式化
                    val_raw = inspire_result_content.get(key, "")
                    val_formatted = format_inspire_field(val_raw)
                    if len(val_formatted) > 1024:
                        val_formatted = val_formatted[:1020] + "..."
                    embed.add_field(name=field_name, value=val_formatted, inline=False)
                    total_len += len(val_formatted)
                
                footer_text = f"由 {model_name} 提供靈感"
                if total_len > 1800: # Discord embed total character limit is around 6000, field value 1024, title 256, desc 4096
                    footer_text = "內容已截斷。 " + footer_text # Simplified message
                
                embed.set_footer(text=footer_text, icon_url="https://brandlogos.net/wp-content/uploads/2025/03/gemini_icon-logo_brandlogos.net_bqzeu.png")
                await interaction.followup.send(embed=embed, ephemeral=True)
                self.logger.info(f"成功發送LLM靈感啟發給 @{interaction.user.name}: channel_id={interaction.channel.id}, problem_id={problem_id}, domain={domain}, content_length={total_len}")
               
            except discord.errors.InteractionResponded:
                await interaction.followup.send("已經回應過此交互，請重新點擊按鈕。", ephemeral=True)
            except Exception as e:
                self.logger.error(f"處理LLM靈感啟發按鈕交互時發生錯誤: {e}", exc_info=True)
                try:
                    await interaction.followup.send(f"LLM 靈感啟發時發生錯誤：{str(e)}", ephemeral=True)
                except: # noqa
                    pass
            finally:
                # Remove from ongoing requests
                await self._cleanup_request(request_key)
        
        # Navigation buttons for user submissions
        elif custom_id.startswith("user_sub_prev_") or custom_id.startswith("user_sub_next_"):
            self.logger.debug(f"接收到使用者解題紀錄導航按鈕交互: custom_id={custom_id}")
            
            try:
                # Parse custom_id: user_sub_[prev/next]_{username}_{current_page}
                parts = custom_id.split("_")
                direction = parts[2]  # "prev" or "next"
                username = "_".join(parts[3:-1])  # Username might contain underscores
                current_page = int(parts[-1])
                
                # Calculate new page
                if direction == "prev":
                    new_page = current_page - 1
                else:  # "next"
                    new_page = current_page + 1
                
                # Get cached submissions or fetch new ones
                cache_key = f"{username}_{interaction.user.id}"
                cached_data = self.submissions_cache.get(cache_key)
                
                # Check if cache is valid (5 minutes)
                if cached_data and (time.time() - cached_data[1]) < 300:
                    submissions = cached_data[0]
                else:
                    # Fetch submissions again
                    await interaction.response.defer(ephemeral=True)
                    # Use the original limit if available, otherwise default to 50
                    original_limit = cached_data[2] if cached_data and len(cached_data) > 2 else 50
                    submissions = await self.bot.lcus.fetch_recent_ac_submissions(username, original_limit)
                    if not submissions:
                        await interaction.followup.send(f"找不到使用者 **{username}** 的解題紀錄。", ephemeral=True)
                        return
                    # Update cache with limit
                    self.submissions_cache[cache_key] = (submissions, time.time(), original_limit)
                
                # Validate page number
                if new_page < 0 or new_page >= len(submissions):
                    await interaction.response.send_message("無效的頁面", ephemeral=True)
                    return
                
                # Create new embed and view
                slash_cog = self.bot.get_cog("SlashCommandsCog")
                if not slash_cog:
                    await interaction.response.send_message("無法載入指令模組", ephemeral=True)
                    return
                
                # Defer if not already done
                if not interaction.response.is_done():
                    await interaction.response.defer(ephemeral=True)
                
                # Get detailed info for the new page
                detailed_submission = await slash_cog._get_submission_details(submissions[new_page])
                if not detailed_submission:
                    await interaction.followup.send("無法載入題目詳細資訊", ephemeral=True)
                    return
                
                embed = slash_cog._create_submission_embed(detailed_submission, new_page, len(submissions), username)
                view = slash_cog._create_submission_view(detailed_submission, new_page, username, len(submissions))
                
                # Update the message
                await interaction.edit_original_response(embed=embed, view=view)
                
                self.logger.info(f"使用者 {interaction.user.name} 瀏覽 {username} 的解題紀錄，第 {new_page + 1}/{len(submissions)} 頁")
                
            except Exception as e:
                self.logger.error(f"處理導航按鈕時發生錯誤: {e}", exc_info=True)
                try:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(f"導航時發生錯誤：{str(e)}", ephemeral=True)
                    else:
                        await interaction.followup.send(f"導航時發生錯誤：{str(e)}", ephemeral=True)
                except:
                    pass

async def setup(bot: commands.Bot):
    await bot.add_cog(InteractionHandlerCog(bot))