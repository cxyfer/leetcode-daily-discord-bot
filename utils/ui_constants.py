"""
UI Constants for Discord Bot
定義所有 Discord UI 相關的常量
"""

# 難度顏色映射
DIFFICULTY_COLORS = {
    "Easy": 0x00FF00,  # 綠色
    "Medium": 0xFFA500,  # 橘色
    "Hard": 0xFF0000,  # 紅色
}

# 難度表情符號映射
DIFFICULTY_EMOJIS = {"Easy": "🟢", "Medium": "🟡", "Hard": "🔴"}

# 洛谷難度表情符號映射
LUOGU_DIFFICULTY_EMOJIS = {
    "暂无评定": "⚪",
    "入门": "🔴",
    "普及-": "🟠",
    "普及/提高-": "🟡",
    "普及+/提高": "🟢",
    "提高+/省选-": "🔵",
    "省选/NOI-": "🟣",
    "NOI/NOI+/CTSC": "⚫",
}

# 無難度題目表情符號
NON_DIFFICULTY_EMOJI = "🧩"

# 預設顏色
DEFAULT_COLOR = 0x0099FF

# 特殊功能顏色
INSPIRATION_COLOR = 0x8E44AD

# 按鈕表情符號
BUTTON_EMOJIS = {
    "description": "📖",
    "translate": "🤖",
    "inspire": "💡",
    "similar": "🔍",
    "previous": "◀️",
    "next": "▶️",
}

# 欄位表情符號
FIELD_EMOJIS = {
    "difficulty": "🔥",
    "rating": "⭐",
    "ac_rate": "📈",
    "tags": "🏷️",
    "similar": "🔍",
    "search": "🔍",
    "instructions": "💡",
    "problems": "📋",
    "link": "🔗",
    "history": "📅",
}

# LeetCode 相關常量
LEETCODE_LOGO_URL = "https://leetcode.com/static/images/LeetCode_logo.png"
GEMINI_LOGO_URL = "https://brandlogos.net/wp-content/uploads/2025/03/gemini_icon-logo_brandlogos.net_bqzeu.png"

# AtCoder 相關常量
ATCODER_LOGO_URL = "https://img.atcoder.jp/assets/logo.png"

# 域名映射
DOMAIN_MAPPING = {
    "com": {
        "name": "LCUS",
        "full_name": "leetcode.com",
        "alt_name": "LCCN",
        "alt_full_name": "leetcode.cn",
    },
    "cn": {
        "name": "LCCN",
        "full_name": "leetcode.cn",
        "alt_name": "LCUS",
        "alt_full_name": "leetcode.com",
    },
}

# 按鈕樣式映射
BUTTON_STYLES = {
    "primary": "primary",
    "secondary": "secondary",
    "success": "success",
    "danger": "danger",
}

# 靈感啟發欄位映射
INSPIRE_FIELDS = {
    "thinking": "🧠 思路",
    "traps": "⚠️ 陷阱",
    "algorithms": "🛠️ 推薦演算法",
    "inspiration": "✨ 其他靈感",
}

# 限制常量
MAX_PROBLEMS_PER_OVERVIEW = 25  # Discord 按鈕限制
PROBLEMS_PER_FIELD = 5  # 每個欄位顯示的題目數量
MAX_SIMILAR_QUESTIONS = 3  # 最多顯示的相似題目數量
MAX_FIELD_LENGTH = 1024  # Discord embed 欄位最大長度
MAX_EMBED_LENGTH = 6000  # Discord embed 總長度限制
