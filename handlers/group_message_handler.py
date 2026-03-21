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
        # 获取基础信息
        platform = event.get_platform_name()
        group_id = event.get_group_id()
        sender_id = event.get_sender_id()
        sender_name = event.get_sender_name()

        self.log_info(
            f"📩 收到消息 | 平台: {platform} | 群: {group_id} | 用户: {sender_name}({sender_id})"
        )

        # 检查平台支持
        if platform != SUPPORTED_PLATFORM:
            self.log_debug(f"⏭️ 跳过: 平台 {platform} 不受支持 (仅支持 {SUPPORTED_PLATFORM})")
            return False

        # 获取群号
        if not group_id:
            self.log_debug("⏭️ 跳过: 无法获取群号")
            return False

        # 检查群白名单
        if not self.context_service.is_group_enabled(group_id):
            enabled_groups = self.config.enabled_groups
            self.log_debug(
                f"⏭️ 跳过: 群 {group_id} 不在白名单中 | 当前白名单: {enabled_groups if enabled_groups else '全部允许'}"
            )
            return False

        self.log_info(f"✅ 群 {group_id} 在白名单中，开始处理")

        # 格式化消息（包含用户名称）
        message_content = MessageUtils.format_message(event)
        if not message_content:
            self.log_debug("⏭️ 跳过: 消息内容为空")
            return False

        # 格式：用户名称：消息内容
        message_text = f"{sender_name}：{message_content}"

        self.log_info(f"📝 消息内容: {message_text[:50]}{'...' if len(message_text) > 50 else ''}")

        # 添加到滑动窗口
        count = self.context_service.add_message(group_id, message_text)
        self.log_info(
            f"📊 群 {group_id} 滑动窗口 | 当前计数: {count}/{self.config.trigger_interval} | "
            f"窗口大小: {self.config.window_size}"
        )

        # 检查是否应触发
        if not self.context_service.should_trigger(
            group_id, self.config.trigger_interval
        ):
            self.log_debug(
                f"⏳ 未达触发条件 | 当前: {count}/{self.config.trigger_interval}"
            )
            return False

        self.log_info(f"🎯 群 {group_id} 满足触发间隔条件")

        # 重置计数器
        self.context_service.reset_counter(group_id)
        self.log_debug(f"🔄 群 {group_id} 计数器已重置")

        # 概率判断
        roll = random.randint(1, 100)
        if roll > self.config.trigger_probability:
            self.log_info(
                f"🎲 概率判定未通过 | 随机数: {roll} | 需要: ≤{self.config.trigger_probability}"
            )
            return False

        self.log_info(
            f"🎲 概率判定通过 | 随机数: {roll} | 阈值: {self.config.trigger_probability}"
        )

        # 设置处理状态，防止重复触发
        self.context_service.set_processing(group_id, True)

        try:
            # 获取语境并分析
            context = self.context_service.get_context(group_id)
            context_text = self.context_service.get_context_text(group_id)
            self.log_info(
                f"📚 群 {group_id} 语境分析 | 窗口消息数: {len(context)} | "
                f"分析策略: {'LLM' if self.analyzer._use_llm_analysis else '关键词'}"
            )
            self.log_debug(f"📄 语境内容:\n{context_text}")

            # 分析语境
            emotion = await self.analyzer.analyze(event, context)

            self.log_info(f"🎭 语境分析结果: {emotion}")

            # 发送表情包
            self.log_info(f"📤 正在发送表情包: {emotion}")
            success = await self.meme_service.send_meme(event, emotion)

            if success:
                self.log_info(f"✅ 群 {group_id} 表情包发送成功")
            else:
                self.log_warning(f"⚠️ 群 {group_id} 表情包发送失败")

            return success

        except Exception as e:
            self.log_error(f"❌ 处理群消息时发生错误: {e}")
            import traceback
            self.log_debug(f"错误堆栈:\n{traceback.format_exc()}")
            return False
        finally:
            # 无论成功或失败，都退出处理状态并重置计数器
            self.context_service.set_processing(group_id, False)
            self.context_service.reset_counter(group_id)
            self.log_debug(f"🔄 群 {group_id} 处理完成，计数器已重置")

    def update_config(self, config: BasicConfig):
        """更新配置。

        Args:
            config: 新的基础配置
        """
        self.config = config
        self.log_debug("配置已更新")
