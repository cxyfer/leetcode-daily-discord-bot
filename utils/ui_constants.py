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

# 預設顏色
DEFAULT_COLOR = 0x0099FF

# 特殊功能顏色
INSPIRATION_COLOR = 0x8E44AD

# 按鈕表情符號
BUTTON_EMOJIS = {
    "description": "📖",
    "translate": "🤖",
    "inspire": "💡",
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
}

# LeetCode 相關常量
LEETCODE_LOGO_URL = "https://leetcode.com/static/images/LeetCode_logo.png"
GEMINI_LOGO_URL = "https://brandlogos.net/wp-content/uploads/2025/03/gemini_icon-logo_brandlogos.net_bqzeu.png"

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

# 限制常量
MAX_PROBLEMS_PER_OVERVIEW = 25  # Discord 按鈕限制
PROBLEMS_PER_FIELD = 5  # 每個欄位顯示的題目數量
MAX_SIMILAR_QUESTIONS = 3  # 最多顯示的相似題目數量
MAX_FIELD_LENGTH = 1024  # Discord embed 欄位最大長度
MAX_EMBED_LENGTH = 6000  # Discord embed 總長度限制
