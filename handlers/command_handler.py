"""命令处理器模块。

处理表情包管理相关的命令。
"""

import os
import time

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from ..backend.category_manager import CategoryManager
from ..config import MEMES_DIR
from ..constants import LOG_PREFIX, SUPPORTED_PLATFORM
from ..services.meme_service import MemeService
from ..models import UploadState
from ..utils.image_utils import ImageUtils
from ..utils.message_utils import MessageUtils


class CommandHandler:
    """命令处理器。

    负责处理表情包管理相关的命令，包括查看图库、添加表情、图库统计等。

    Attributes:
        category_manager: 类别管理器
        meme_service: 表情包服务
        upload_states: 上传状态字典
    """

    def __init__(
        self,
        category_manager: CategoryManager,
        meme_service: MemeService,
    ):
        """初始化命令处理器。

        Args:
            category_manager: 类别管理器
            meme_service: 表情包服务
        """
        self.name = "CommandHandler"
        self.category_manager = category_manager
        self.meme_service = meme_service
        self.upload_states: dict[str, UploadState] = {}

    async def list_emotions(self, event: AstrMessageEvent):
        """查看所有可用表情包类别。

        Args:
            event: AstrBot 消息事件
        """
        descriptions = self.category_manager.get_descriptions()
        if not descriptions:
            yield event.plain_result("🖼️ 当前图库为空")
            return

        categories = "\n".join(
            [f"- {tag}: {desc}" for tag, desc in descriptions.items()]
        )
        yield event.plain_result(f"🖼️ 当前图库：\n{categories}")

    async def upload_meme(self, event: AstrMessageEvent, category: str = None):
        """上传表情包到指定类别。

        Args:
            event: AstrBot 消息事件
            category: 目标类别名称
        """
        if not category:
            yield event.plain_result(
                "📌 若要添加表情，请按照此格式操作：\n"
                "/表情管理 添加表情 [类别名称]\n"
                "（输入 /查看图库 可获取类别列表）"
            )
            return

        descriptions = self.category_manager.get_descriptions()
        if category not in descriptions:
            yield event.plain_result(
                f"您输入的表情包类别「{category}」是无效的哦。\n"
                f"可以使用 /查看图库 来查看可用的类别。"
            )
            return

        # 仅支持 aiocqhttp 平台
        if event.get_platform_name() != SUPPORTED_PLATFORM:
            yield event.plain_result("⚠️ 该功能仅支持 aiocqhttp 平台（QQ个人号）")
            return

        user_key = self._get_user_key(event)
        self.upload_states[user_key] = UploadState(
            category=category,
            expire_time=time.time() + 30,
        )
        yield event.plain_result(
            f"请在30秒内发送要添加到【{category}】类别的图片（可发送多张图片）。"
        )

    async def handle_upload_image(self, event: AstrMessageEvent):
        """处理用户上传的图片。

        Args:
            event: AstrBot 消息事件
        """
        # 仅支持 aiocqhttp 平台
        if event.get_platform_name() != SUPPORTED_PLATFORM:
            return

        user_key = self._get_user_key(event)
        upload_state = self.upload_states.get(user_key)

        if not upload_state or time.time() > upload_state.expire_time:
            if user_key in self.upload_states:
                del self.upload_states[user_key]
            return

        # 提取图片
        images = MessageUtils.extract_images(event)
        if not images:
            yield event.plain_result("请发送图片文件来进行上传哦。")
            return

        category = upload_state.category
        save_dir = os.path.join(MEMES_DIR, category)

        try:
            os.makedirs(save_dir, exist_ok=True)
            saved_files = []

            for idx, img in enumerate(images, 1):
                try:
                    # 下载图片
                    content = await ImageUtils.download_image(img.url)
                    if not content:
                        continue

                    # 检测格式
                    image_format = ImageUtils.detect_format(content)
                    ext = ImageUtils.get_extension(image_format)

                    # 保存图片
                    timestamp = int(time.time())
                    filename = f"{timestamp}_{idx}{ext}"
                    save_path = os.path.join(save_dir, filename)

                    if ImageUtils.save_image(content, save_path):
                        saved_files.append(filename)

                except Exception as e:
                    logger.error(f"{LOG_PREFIX} 处理图片失败: {e}")
                    continue

            # 清理上传状态
            del self.upload_states[user_key]

            if saved_files:
                yield event.plain_result(
                    f"✅ 已经成功收录了 {len(saved_files)} 张新表情到「{category}」图库！"
                )
                # 重新加载表情
                self.category_manager.sync_with_filesystem()
            else:
                yield event.plain_result(
                    "❌ 没有成功保存任何图片，请检查图片格式是否正确。"
                )

        except Exception as e:
            logger.error(f"{LOG_PREFIX} 保存图片失败: {e}")
            yield event.plain_result(f"保存失败了：{str(e)}")

    async def show_stats(self, event: AstrMessageEvent):
        """显示图库详细统计信息。

        Args:
            event: AstrBot 消息事件
        """
        try:
            stats = self.meme_service.get_emotion_stats()

            result = ["📊 表情包图库统计报告", ""]

            if stats:
                total = sum(stats.values())
                result.append("📁 本地图库统计:")
                result.append(f"  • 总文件数: {total} 个")
                result.append(f"  • 分类数: {len(stats)} 个")
                result.append("")
                result.append("📂 本地分类详情:")
                for cat, count in sorted(
                    stats.items(), key=lambda x: x[1], reverse=True
                ):
                    result.append(f"  • {cat}: {count} 个")

                # 存储空间估算
                result.append("")
                result.append("💾 存储空间估算:")
                estimated_size = total * 500 / 1024
                result.append(f"  • 本地图库约: {estimated_size:.1f} MB")
            else:
                result.append("📁 本地图库为空")

            yield event.plain_result("\n".join(result))

        except Exception as e:
            logger.error(f"{LOG_PREFIX} 获取图库统计失败: {e}")
            yield event.plain_result(f"获取图库统计失败: {str(e)}")

    def _get_user_key(self, event: AstrMessageEvent) -> str:
        """获取用户唯一标识。

        Args:
            event: AstrBot 消息事件

        Returns:
            用户唯一标识
        """
        return f"{event.session_id}_{event.get_sender_id()}"

    def cleanup_expired_states(self):
        """清理过期的上传状态。"""
        current_time = time.time()
        expired_keys = [
            key
            for key, state in self.upload_states.items()
            if current_time > state.expire_time
        ]
        for key in expired_keys:
            del self.upload_states[key]

        if expired_keys:
            logger.debug(f"{LOG_PREFIX} 清理了 {len(expired_keys)} 个过期上传状态")
