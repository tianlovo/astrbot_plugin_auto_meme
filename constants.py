"""常量定义模块。

包含插件中使用的所有常量和映射关系。
"""

# 消息类型到文本表示的映射
MESSAGE_TYPE_MAP = {
    "Plain": lambda c: c.text if hasattr(c, "text") else "",
    "Image": lambda c: "[图片]",
    "Face": lambda c: "[表情]",
    "Record": lambda c: "[语音]",
    "Video": lambda c: "[视频]",
    "File": lambda c: "[文件]",
    "At": lambda c: "[@用户]",
    "Reply": lambda c: "[回复]",
}

# 表情包关键词映射
EMOTION_KEYWORDS = {
    "happy": [
        "开心",
        "高兴",
        "哈哈",
        "笑",
        "好耶",
        "棒",
        "不错",
        "好的",
        "可以",
        "赞",
        "喜欢",
        "爱",
    ],
    "angry": [
        "生气",
        "愤怒",
        "可恶",
        "气死",
        "烦",
        "讨厌",
        "滚",
        "妈的",
        "艹",
        "fuck",
        "shit",
    ],
    "sad": ["难过", "伤心", "哭", "呜呜", "悲伤", "泪", "难受", "痛苦", "委屈"],
    "confused": ["疑惑", "问号", "???", "不懂", "什么", "为啥", "为什么", "怎么"],
    "cpu": ["cpu", "烧脑", "复杂", "难懂", "看不懂", "绕", "晕"],
    "fool": ["笨蛋", "傻", "蠢", "憨", "呆", "弱智", "脑瘫"],
    "givemoney": ["钱", "红包", "打赏", "付费", "穷", "富", "富婆"],
    "like": ["喜欢", "爱", "心动", "好感", "贴贴", "抱抱"],
    "meow": ["喵", "猫", "猫猫", " kitten"],
    "morning": ["早安", "早上好", "早", "起床"],
    "reply": ["回复", "回答", "解答", "解释"],
    "see": ["看", "瞧", "瞅", "围观", "吃瓜"],
    "shy": ["害羞", "羞", "脸红", "不好意思", "尴尬"],
    "sigh": ["叹气", "无奈", "唉", "啊这", "无语"],
    "sleep": ["睡觉", "困", "晚安", "睡了", "眠"],
    "baka": ["笨蛋", "八嘎", "baka", "蠢", "傻"],
    "color": ["色", "好色", "h", "黄", "涩", "色图"],
}

# 默认配置值
DEFAULT_WINDOW_SIZE = 30
DEFAULT_TRIGGER_INTERVAL = 5
DEFAULT_TRIGGER_PROBABILITY = 50
DEFAULT_CONVERT_STATIC_TO_GIF = False
DEFAULT_USE_LLM_ANALYSIS = True

# 默认LLM提示词
DEFAULT_SYSTEM_PROMPT = """你是一个专业的群聊语境分析助手。请根据提供的群聊消息历史，分析当前对话的氛围和情绪，选择最合适的表情包类别。

当前时间：{current_time}

可用的表情包类别及其使用场景：
{emotions_list}

时间限制说明：
- morning（早安）：仅在 06:00-11:59 可发送
- sleep（睡觉）：仅在 21:00-02:59 可发送

重要：请仅返回类别名称，不要有任何解释或额外内容。如果无法确定，请返回 "random"。"""

DEFAULT_USER_PROMPT = """请分析以下群聊消息，选择最合适的表情包类别：

{context_text}

最合适的类别是："""

# 支持的图片格式
SUPPORTED_IMAGE_FORMATS = (".jpg", ".jpeg", ".png", ".gif", ".webp")

# 平台限制
SUPPORTED_PLATFORM = "aiocqhttp"

# 日志前缀
LOG_PREFIX = "[meme_auto]"
