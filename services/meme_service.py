"""表情包服务模块。

封装表情包选择、转换、发送逻辑。
"""

import os
import random
import tempfile
import time
from datetime import datetime
from pathlib import Path

from PIL import Image as PILImage

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent
from astrbot.api.message_components import Image
from astrbot.core.message.message_event_result import MessageChain

from ..config import MEMES_DIR
from ..constants import LOG_PREFIX, SUPPORTED_IMAGE_FORMATS
from ..types import MemeInfo


# 时间限制配置
TIME_RESTRICTED_CATEGORIES = {
    "morning": {"start": 6, "end": 11},  # 早上 6:00 - 11:59
    "sleep": {"start": 21, "end": 2},    # 晚上 21:00 - 次日 2:59
}


class MemeService:
    """表情包服务类。

    负责表情包的获取、格式转换和发送。

    Attributes:
        memes_dir: 表情包目录路径
        convert_static_to_gif: 是否将静态图转换为GIF
        timezone: 时区设置
    """

    def __init__(self, memes_dir: Path = None, convert_static_to_gif: bool = False, timezone: str = "Asia/Shanghai"):
        """初始化表情包服务。

        Args:
            memes_dir: 表情包目录路径，默认使用 config.MEMES_DIR
            convert_static_to_gif: 是否将静态图转换为GIF格式
            timezone: 时区设置，默认 Asia/Shanghai
        """
        self.memes_dir = memes_dir or MEMES_DIR
        self.convert_static_to_gif = convert_static_to_gif
        self.timezone = timezone

    def get_random_meme(self, emotion: str) -> MemeInfo | None:
        """获取指定类别的随机表情包。

        Args:
            emotion: 表情包类别名称

        Returns:
            MemeInfo对象，如果类别不存在或为空则返回None
        """
        emotion_path = self.memes_dir / emotion
        if not emotion_path.exists():
            logger.warning(f"{LOG_PREFIX} 表情包类别 {emotion} 目录不存在")
            return None

        memes = [
            f
            for f in emotion_path.iterdir()
            if f.is_file() and f.suffix.lower() in SUPPORTED_IMAGE_FORMATS
        ]

        if not memes:
            logger.warning(f"{LOG_PREFIX} 表情包类别 {emotion} 没有图片")
            return None

        selected = random.choice(memes)
        return MemeInfo(emotion=emotion, filename=selected.name, path=str(selected))

    def convert_to_gif(self, image_path: str) -> str:
        """将静态图片转换为 GIF 格式。

        如果 convert_static_to_gif 为 False 或图片已经是 GIF，
        则直接返回原路径。

        Args:
            image_path: 原始图片路径

        Returns:
            转换后的GIF路径，或原路径（如果不需要转换）
        """
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
                logger.debug(f"{LOG_PREFIX} 已将静态图转换为 GIF: {temp_filename}")
                return temp_filename
        except Exception as e:
            logger.error(f"{LOG_PREFIX} 转换图片为 GIF 失败: {e}")
            return image_path

    def _check_time_restriction(self, emotion: str) -> bool:
        """检查表情包类别是否在允许的时间范围内。

        Args:
            emotion: 表情包类别名称

        Returns:
            如果在允许的时间范围内返回 True，否则返回 False
        """
        if emotion not in TIME_RESTRICTED_CATEGORIES:
            return True

        try:
            from zoneinfo import ZoneInfo

            # 获取当前时间（指定时区）
            now = datetime.now(ZoneInfo(self.timezone))
            current_hour = now.hour

            restriction = TIME_RESTRICTED_CATEGORIES[emotion]
            start_hour = restriction["start"]
            end_hour = restriction["end"]

            # 处理跨天的情况（如 sleep: 21:00 - 02:59）
            if start_hour > end_hour:
                # 跨天时间段（如 21:00 - 02:59）
                allowed = current_hour >= start_hour or current_hour <= end_hour
            else:
                # 当天时间段（如 06:00 - 11:59）
                allowed = start_hour <= current_hour <= end_hour

            if not allowed:
                logger.info(
                    f"{LOG_PREFIX} ⏰ 类别 '{emotion}' 不在允许的时间范围内 | "
                    f"当前时间: {now.strftime('%Y-%m-%d %H:%M')} | "
                    f"允许时段: {start_hour}:00-{end_hour}:59"
                )

            return allowed
        except Exception as e:
            logger.error(f"{LOG_PREFIX} 检查时间限制失败: {e}")
            return True  # 出错时允许发送

    async def send_meme(self, event: AstrMessageEvent, emotion: str) -> bool:
        """发送指定类别的表情包。

        Args:
            event: 消息事件对象
            emotion: 表情包类别名称

        Returns:
            发送是否成功
        """
        logger.info(f"{LOG_PREFIX} 🖼️ 开始获取表情包 | 类别: {emotion}")

        # 检查时间限制
        if not self._check_time_restriction(emotion):
            logger.info(f"{LOG_PREFIX} ⏰ 跳过发送 | 类别 '{emotion}' 当前不在允许的时间范围内")
            return False

        meme_info = self.get_random_meme(emotion)
        if not meme_info:
            logger.warning(f"{LOG_PREFIX} ⚠️ 无法获取表情包 | 类别 '{emotion}' 不存在或为空")
            return False

        logger.info(
            f"{LOG_PREFIX} ✅ 选中表情包 | 类别: {meme_info.emotion} | "
            f"文件: {meme_info.filename}"
        )

        final_meme_file = self.convert_to_gif(meme_info.path)

        if final_meme_file != meme_info.path:
            logger.debug(f"{LOG_PREFIX} 🔄 图片已转换为 GIF: {final_meme_file}")

        try:
            logger.info(f"{LOG_PREFIX} 📤 正在发送表情包...")
            await event.send(MessageChain([Image.fromFileSystem(final_meme_file)]))
            logger.info(
                f"{LOG_PREFIX} ✅ 表情包发送成功 | 类别: {emotion} | 文件: {meme_info.filename}"
            )

            # 清理临时文件
            if final_meme_file != meme_info.path and os.path.exists(final_meme_file):
                try:
                    os.remove(final_meme_file)
                    logger.debug(f"{LOG_PREFIX} 🗑️ 临时文件已清理: {final_meme_file}")
                except Exception as e:
                    logger.debug(f"{LOG_PREFIX} ⚠️ 清理临时文件失败: {e}")

            return True
        except Exception as e:
            logger.error(f"{LOG_PREFIX} ❌ 发送表情包失败: {e}")
            return False

    def get_available_emotions(self) -> list[str]:
        """获取所有可用的表情包类别。

        Returns:
            类别名称列表
        """
        if not self.memes_dir.exists():
            return []

        return [
            d.name
            for d in self.memes_dir.iterdir()
            if d.is_dir()
            and any(
                f.suffix.lower() in SUPPORTED_IMAGE_FORMATS
                for f in d.iterdir()
                if f.is_file()
            )
        ]

    def get_emotion_stats(self) -> dict[str, int]:
        """获取各类别表情包数量统计。

        Returns:
            类别名称到数量的映射字典
        """
        stats = {}
        if not self.memes_dir.exists():
            return stats

        for emotion_dir in self.memes_dir.iterdir():
            if not emotion_dir.is_dir():
                continue

            count = len(
                [
                    f
                    for f in emotion_dir.iterdir()
                    if f.is_file() and f.suffix.lower() in SUPPORTED_IMAGE_FORMATS
                ]
            )
            if count > 0:
                stats[emotion_dir.name] = count

        return stats
