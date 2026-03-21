"""群消息处理器模块。

处理群消息事件，维护滑动窗口并触发表情包发送。
"""

import random

from astrbot.api.event import AstrMessageEvent

from ..constants import SUPPORTED_PLATFORM
from ..core.context_analyzer import ContextAnalyzer
from ..services.group_context_service import GroupContextService
from ..services.meme_service import MemeService
from ..types import BasicConfig
from ..utils.message_utils import MessageUtils
from .base_handler import BaseHandler


class GroupMessageHandler(BaseHandler):
    """群消息处理器。

    负责监听群消息、维护滑动窗口、触发语境分析和表情包发送。

    Attributes:
        config: 基础配置
        context_service: 群组上下文服务
        analyzer: 语境分析器
        meme_service: 表情包服务
    """

    def __init__(
        self,
        config: BasicConfig,
        context_service: GroupContextService,
        analyzer: ContextAnalyzer,
        meme_service: MemeService,
    ):
        """初始化群消息处理器。

        Args:
            config: 基础配置
            context_service: 群组上下文服务
            analyzer: 语境分析器
            meme_service: 表情包服务
        """
        super().__init__("GroupMessageHandler")
        self.config = config
        self.context_service = context_service
        self.analyzer = analyzer
        self.meme_service = meme_service

    async def handle(self, event: AstrMessageEvent, **kwargs) -> bool:
        """处理群消息事件。

        Args:
            event: AstrBot 消息事件

        Returns:
            是否成功处理（是否发送了表情包）
        """
        # 检查平台支持
        if event.get_platform_name() != SUPPORTED_PLATFORM:
            return False

        # 获取群号
        group_id = event.get_group_id()
        if not group_id:
            return False

        # 检查群白名单
        if not self.context_service.is_group_enabled(group_id):
            return False

        # 格式化消息
        message_text = MessageUtils.format_message(event)
        if not message_text:
            return False

        # 添加到滑动窗口
        count = self.context_service.add_message(group_id, message_text)
        self.log_debug(f"群 {group_id} 消息计数: {count}")

        # 检查是否应触发
        if not self.context_service.should_trigger(
            group_id, self.config.trigger_interval
        ):
            return False

        # 重置计数器
        self.context_service.reset_counter(group_id)

        # 概率判断
        if random.randint(1, 100) > self.config.trigger_probability:
            self.log_debug("概率未通过，不发送表情包")
            return False

        try:
            # 分析语境并发送表情包
            context = self.context_service.get_context(group_id)
            emotion = await self.analyzer.analyze(context, event)

            self.log_info(f"群 {group_id} 触发表情包发送，选择类别: {emotion}")
            success = await self.meme_service.send_meme(event, emotion)

            return success

        except Exception as e:
            self.log_error(f"处理群消息失败: {e}")
            return False

    def update_config(self, config: BasicConfig):
        """更新配置。

        Args:
            config: 新的基础配置
        """
        self.config = config
        self.log_debug("配置已更新")
