import os
import random
import re
import tempfile
import time

from PIL import Image as PILImage

from astrbot.api import logger
from astrbot.api.all import *
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.event.filter import EventMessageType
from astrbot.api.message_components import *
from astrbot.api.star import Context, Star, register
from astrbot.core.message.message_event_result import MessageChain

from .backend.category_manager import CategoryManager
from .config import DEFAULT_CATEGORY_DESCRIPTIONS, MEMES_DATA_PATH, MEMES_DIR
from .group_context_manager import GroupContextManager
from .init import init_plugin
from .utils import load_json

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


@register("meme_manager", "anka", "anka - 表情包管理器 - 基于群聊语境主动发送", "4.0")
class MemeSender(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.config = config or {}

        # 初始化插件
        if not init_plugin():
            raise RuntimeError("插件初始化失败")

        # 初始化类别管理器
        self.category_manager = CategoryManager()

        # 初始化群组上下文管理器
        window_size = self.config.get("window_size", 30)
        self.group_context = GroupContextManager(window_size=window_size)

        # 读取配置（适配父级结构）
        basic_config = self.config.get("basic", {})
        self.enabled_groups = basic_config.get("enabled_groups", [])
        self.trigger_interval = basic_config.get("trigger_interval", 5)
        self.trigger_probability = basic_config.get("trigger_probability", 50)
        self.convert_static_to_gif = basic_config.get("convert_static_to_gif", False)

        llm_config = self.config.get("llm_analysis", {})
        self.use_llm_analysis = llm_config.get("use_llm_analysis", True)
        self.llm_system_prompt = llm_config.get("llm_system_prompt", "")
        self.llm_user_prompt = llm_config.get("llm_user_prompt", "")

        # 加载表情包类别映射
        self.category_mapping = load_json(
            MEMES_DATA_PATH, DEFAULT_CATEGORY_DESCRIPTIONS
        )

        logger.info(
            f"表情包管理器已初始化，窗口大小: {window_size}, 触发间隔: {self.trigger_interval}, LLM分析: {self.use_llm_analysis}"
        )

    def _is_group_enabled(self, group_id: str) -> bool:
        """检查群号是否在白名单中"""
        if not self.enabled_groups:
            return True
        return str(group_id) in [str(g) for g in self.enabled_groups]

    def _format_message(self, event: AstrMessageEvent) -> str:
        """将消息格式化为文本表示"""
        parts = []
        for component in event.message_obj.message:
            comp_type = type(component).__name__
            if comp_type in MESSAGE_TYPE_MAP:
                text = MESSAGE_TYPE_MAP[comp_type](component)
                if text:
                    parts.append(text)
            elif hasattr(component, "text"):
                parts.append(component.text)
        return " ".join(parts)

    def _analyze_context_by_keywords(self, messages: list) -> str:
        """基于关键词分析语境，返回最合适的表情包类别"""
        if not messages:
            return random.choice(list(self.category_mapping.keys()))

        # 合并所有消息文本
        context_text = "\n".join(messages)

        # 统计每个类别的关键词匹配次数
        scores = {}
        for emotion, keywords in EMOTION_KEYWORDS.items():
            if emotion not in self.category_mapping:
                continue
            score = 0
            for keyword in keywords:
                count = len(re.findall(re.escape(keyword), context_text, re.IGNORECASE))
                score += count
            if score > 0:
                scores[emotion] = score

        if not scores:
            # 没有匹配到关键词，随机选择
            return random.choice(list(self.category_mapping.keys()))

        # 选择得分最高的类别
        max_score = max(scores.values())
        best_emotions = [e for e, s in scores.items() if s == max_score]
        return random.choice(best_emotions)

    async def _analyze_context_by_llm(
        self, event: AstrMessageEvent, messages: list
    ) -> str:
        """使用LLM分析语境，返回最合适的表情包类别"""
        if not messages:
            return random.choice(list(self.category_mapping.keys()))

        # 合并所有消息文本
        context_text = "\n".join(messages)

        # 构建可用的表情包类别列表
        available_emotions = list(self.category_mapping.keys())
        emotions_list = ", ".join(available_emotions)

        # 构建系统提示词
        default_system_prompt = """你是一个专业的群聊语境分析助手。请根据提供的群聊消息历史，分析当前对话的氛围和情绪，选择最合适的表情包类别。

可用的表情包类别：
{emotions_list}

请只返回一个类别名称，不要有任何解释。如果无法确定，请返回 "random"。"""

        # 使用自定义提示词或默认提示词
        if self.llm_system_prompt:
            system_prompt = self.llm_system_prompt.format(emotions_list=emotions_list)
        else:
            system_prompt = default_system_prompt.format(emotions_list=emotions_list)

        # 构建用户提示词
        default_user_prompt = """请分析以下群聊消息，选择最合适的表情包类别：

{context_text}

最合适的类别是："""

        # 使用自定义提示词或默认提示词
        if self.llm_user_prompt:
            user_prompt = self.llm_user_prompt.format(context_text=context_text)
        else:
            user_prompt = default_user_prompt.format(context_text=context_text)

        try:
            # 获取当前会话的 Provider ID
            umo = event.unified_msg_origin
            provider_id = await self.context.get_current_chat_provider_id(umo=umo)

            if not provider_id:
                logger.warning(
                    "[meme_manager] 无法获取 LLM provider ID，使用关键词分析"
                )
                return self._analyze_context_by_keywords(messages)

            # 调用 LLM
            llm_resp = await self.context.llm_generate(
                chat_provider_id=provider_id,
                prompt=user_prompt,
                system_prompt=system_prompt,
            )

            # 解析 LLM 响应
            result = llm_resp.completion_text.strip().lower()

            # 清理结果，只保留类别名称
            result = re.sub(r"[^\w]", "", result)

            if result == "random" or result not in available_emotions:
                # LLM 无法确定或返回了无效的类别，随机选择
                return random.choice(available_emotions)

            logger.info(f"[meme_manager] LLM 分析结果: {result}")
            return result

        except Exception as e:
            logger.error(f"[meme_manager] LLM 分析失败: {e}")
            # LLM 分析失败，回退到关键词分析
            return self._analyze_context_by_keywords(messages)

    async def _analyze_context(self, event: AstrMessageEvent, messages: list) -> str:
        """分析语境，返回最合适的表情包类别"""
        if self.use_llm_analysis:
            return await self._analyze_context_by_llm(event, messages)
        else:
            return self._analyze_context_by_keywords(messages)

    def _convert_to_gif(self, image_path: str) -> str:
        """将静态图片转换为 GIF 格式"""
        if not self.convert_static_to_gif:
            return image_path

        if image_path.lower().endswith(".gif"):
            return image_path

        try:
            with PILImage.open(image_path) as img:
                if img.format == "GIF":
                    return image_path

                temp_dir = tempfile.gettempdir()
                temp_filename = os.path.join(
                    temp_dir,
                    f"meme_{int(time.time())}_{random.randint(1000, 9999)}.gif",
                )

                if img.mode in ("RGBA", "LA") or (
                    img.mode == "P" and "transparency" in img.info
                ):
                    background = PILImage.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "P":
                        img = img.convert("RGBA")
                    background.paste(img, mask=img.split()[3])
                    img = background
                else:
                    img = img.convert("RGB")

                img.save(temp_filename, "GIF")
                logger.debug(f"[meme_manager] 已将静态图转换为 GIF: {temp_filename}")
                return temp_filename
        except Exception as e:
            logger.error(f"[meme_manager] 转换图片为 GIF 失败: {e}")
            return image_path

    async def _send_meme(self, event: AstrMessageEvent, emotion: str) -> bool:
        """发送指定类别的表情包"""
        emotion_path = os.path.join(MEMES_DIR, emotion)
        if not os.path.exists(emotion_path):
            logger.warning(f"表情包类别 {emotion} 目录不存在")
            return False

        memes = [
            f for f in os.listdir(emotion_path) if f.endswith((".jpg", ".png", ".gif"))
        ]

        if not memes:
            logger.warning(f"表情包类别 {emotion} 没有图片")
            return False

        meme = random.choice(memes)
        meme_file = os.path.join(emotion_path, meme)
        final_meme_file = self._convert_to_gif(meme_file)

        try:
            await event.send(MessageChain([Image.fromFileSystem(final_meme_file)]))
            logger.info(f"[meme_manager] 已发送表情包: {emotion}/{meme}")

            # 清理临时文件
            if final_meme_file != meme_file and os.path.exists(final_meme_file):
                try:
                    os.remove(final_meme_file)
                except Exception:
                    pass

            return True
        except Exception as e:
            logger.error(f"[meme_manager] 发送表情包失败: {e}")
            return False

    @filter.event_message_type(EventMessageType.GROUP_MESSAGE)
    async def on_group_message(self, event: AstrMessageEvent):
        """监听群消息，维护滑动窗口并触发表情包发送"""
        # 仅支持 aiocqhttp 平台
        if event.get_platform_name() != "aiocqhttp":
            return

        # 获取群号
        group_id = event.get_group_id()
        if not group_id:
            return

        # 检查群是否在白名单中
        if not self._is_group_enabled(group_id):
            return

        # 格式化消息
        message_text = self._format_message(event)
        if not message_text:
            return

        # 添加到滑动窗口
        count = self.group_context.add_message(group_id, message_text)
        logger.debug(f"[meme_manager] 群 {group_id} 消息计数: {count}")

        # 检查是否应触发
        if not self.group_context.should_trigger(group_id, self.trigger_interval):
            return

        # 重置计数器
        self.group_context.reset_counter(group_id)

        # 概率判断
        if random.randint(1, 100) > self.trigger_probability:
            logger.debug("[meme_manager] 概率未通过，不发送表情包")
            return

        # 分析语境并发送表情包
        context = self.group_context.get_context(group_id)
        emotion = await self._analyze_context(event, context)

        logger.info(f"[meme_manager] 群 {group_id} 触发表情包发送，选择类别: {emotion}")
        await self._send_meme(event, emotion)

    @filter.command_group("表情管理")
    def meme_manager(self):
        """表情包管理命令组:
        查看图库
        添加表情
        图库统计
        """
        pass

    @meme_manager.command("查看图库")
    async def list_emotions(self, event: AstrMessageEvent):
        """查看所有可用表情包类别"""
        descriptions = self.category_mapping
        categories = "\n".join(
            [f"- {tag}: {desc}" for tag, desc in descriptions.items()]
        )
        yield event.plain_result(f"🖼️ 当前图库：\n{categories}")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @meme_manager.command("添加表情")
    async def upload_meme(self, event: AstrMessageEvent, category: str = None):
        """上传表情包到指定类别"""
        if not category:
            yield event.plain_result(
                "📌 若要添加表情，请按照此格式操作：\n/表情管理 添加表情 [类别名称]\n（输入/查看图库 可获取类别列表）"
            )
            return

        if category not in self.category_manager.get_descriptions():
            yield event.plain_result(
                f"您输入的表情包类别「{category}」是无效的哦。\n可以使用/查看图库来查看可用的类别。"
            )
            return

        # 仅支持 aiocqhttp 平台
        if event.get_platform_name() != "aiocqhttp":
            yield event.plain_result("⚠️ 该功能仅支持 aiocqhttp 平台（QQ个人号）")
            return

        user_key = f"{event.session_id}_{event.get_sender_id()}"
        self.upload_states[user_key] = {
            "category": category,
            "expire_time": time.time() + 30,
        }
        yield event.plain_result(
            f"请在30秒内发送要添加到【{category}】类别的图片（可发送多张图片）。"
        )

    @filter.event_message_type(EventMessageType.ALL)
    async def handle_upload_image(self, event: AstrMessageEvent):
        """处理用户上传的图片"""
        # 仅支持 aiocqhttp 平台
        if event.get_platform_name() != "aiocqhttp":
            return

        user_key = f"{event.session_id}_{event.get_sender_id()}"
        upload_state = self.upload_states.get(user_key)

        if not upload_state or time.time() > upload_state["expire_time"]:
            if user_key in self.upload_states:
                del self.upload_states[user_key]
            return

        images = [c for c in event.message_obj.message if isinstance(c, Image)]

        if not images:
            yield event.plain_result("请发送图片文件来进行上传哦。")
            return

        category = upload_state["category"]
        save_dir = os.path.join(MEMES_DIR, category)

        try:
            os.makedirs(save_dir, exist_ok=True)
            saved_files = []

            for idx, img in enumerate(images, 1):
                timestamp = int(time.time())

                try:
                    # 下载图片
                    import aiohttp

                    ssl_context = __import__("ssl").create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = __import__("ssl").CERT_NONE

                    async with aiohttp.ClientSession(
                        connector=aiohttp.TCPConnector(ssl=ssl_context)
                    ) as session:
                        async with session.get(img.url) as resp:
                            content = await resp.read()

                    try:
                        with PILImage.open(__import__("io").BytesIO(content)) as img:
                            file_type = img.format.lower()
                    except Exception as e:
                        logger.error(f"图片格式检测失败: {str(e)}")
                        file_type = "unknown"

                    ext_mapping = {
                        "jpeg": ".jpg",
                        "png": ".png",
                        "gif": ".gif",
                        "webp": ".webp",
                    }
                    ext = ext_mapping.get(file_type, ".bin")
                    filename = f"{timestamp}_{idx}{ext}"
                    save_path = os.path.join(save_dir, filename)

                    with open(save_path, "wb") as f:
                        f.write(content)
                    saved_files.append(filename)

                except Exception as e:
                    logger.error(f"下载图片失败: {str(e)}")
                    yield event.plain_result(f"文件下载失败: {str(e)}")
                    continue

            del self.upload_states[user_key]

            yield event.plain_result(
                f"✅ 已经成功收录了 {len(saved_files)} 张新表情到「{category}」图库！"
            )
            await self.reload_emotions()

        except Exception as e:
            yield event.plain_result(f"保存失败了：{str(e)}")

    async def reload_emotions(self):
        """动态重新加载表情配置"""
        try:
            self.category_manager.sync_with_filesystem()
            self.category_mapping = load_json(
                MEMES_DATA_PATH, DEFAULT_CATEGORY_DESCRIPTIONS
            )
        except Exception as e:
            logger.error(f"重新加载表情配置失败: {str(e)}")

    @meme_manager.command("图库统计")
    async def show_library_stats(self, event: AstrMessageEvent):
        """显示图库详细统计信息"""
        try:
            result = ["📊 表情包图库统计报告", "", "📁 本地图库统计:"]

            # 统计本地文件
            local_stats = {}
            local_total = 0

            if os.path.exists(MEMES_DIR):
                for category in os.listdir(MEMES_DIR):
                    category_path = os.path.join(MEMES_DIR, category)
                    if os.path.isdir(category_path):
                        files = [
                            f
                            for f in os.listdir(category_path)
                            if f.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp"))
                        ]
                        count = len(files)
                        local_stats[category] = count
                        local_total += count

            # 显示本地统计
            if local_stats:
                result.append(f"  • 总文件数: {local_total} 个")
                result.append(f"  • 分类数: {len(local_stats)} 个")
                result.append("")
                result.append("📂 本地分类详情:")
                for cat, count in sorted(
                    local_stats.items(), key=lambda x: x[1], reverse=True
                ):
                    result.append(f"  • {cat}: {count} 个")
            else:
                result.append("  • 本地图库为空")

            # 存储空间估算
            result.append("")
            result.append("💾 存储空间估算:")
            if local_total > 0:
                estimated_size = local_total * 500 / 1024
                result.append(f"  • 本地图库约: {estimated_size:.1f} MB")

            yield event.plain_result("\n".join(result))

        except Exception as e:
            logger.error(f"获取图库统计失败: {str(e)}")
            yield event.plain_result(f"获取图库统计失败: {str(e)}")

    async def terminate(self):
        """清理资源"""
        logger.info("表情包管理器已关闭")
