"""群组上下文服务模块。

封装群组消息窗口管理和触发逻辑。
"""

from astrbot.api import logger

from ..constants import LOG_PREFIX
from ..group_context_manager import GroupContextManager
from ..types import BasicConfig


class GroupContextService:
    """群组上下文服务类。

    负责管理群组消息的滑动窗口、触发判断和白名单检查。

    Attributes:
        context_manager: 群组上下文管理器实例
        config: 基础配置
    """

    def __init__(self, config: BasicConfig):
        """初始化群组上下文服务。

        Args:
            config: 基础配置对象
        """
        self.config = config
        self.context_manager = GroupContextManager(window_size=config.window_size)
        logger.debug(
            f"{LOG_PREFIX} 群组上下文服务已初始化，窗口大小: {config.window_size}"
        )

    def add_message(self, group_id: str, message: str) -> int:
        """添加消息到指定群的滑动窗口。

        Args:
            group_id: 群号
            message: 消息内容

        Returns:
            当前消息计数
        """
        count = self.context_manager.add_message(group_id, message)
        logger.debug(f"{LOG_PREFIX} 群 {group_id} 消息计数: {count}")
        return count

    def should_trigger(self, group_id: str, interval: int = None) -> bool:
        """判断是否应触发表情包发送。

        Args:
            group_id: 群号
            interval: 触发间隔（消息数），默认使用配置中的值

        Returns:
            是否应触发
        """
        trigger_interval = interval or self.config.trigger_interval
        should_trigger = self.context_manager.should_trigger(group_id, trigger_interval)
        if should_trigger:
            logger.debug(
                f"{LOG_PREFIX} 群 {group_id} 满足触发条件（间隔: {trigger_interval}）"
            )
        return should_trigger

    def reset_counter(self, group_id: str):
        """重置指定群的消息计数器。

        Args:
            group_id: 群号
        """
        self.context_manager.reset_counter(group_id)
        logger.debug(f"{LOG_PREFIX} 群 {group_id} 计数器已重置")

    def get_context(self, group_id: str) -> list[str]:
        """获取指定群的窗口内容。

        Args:
            group_id: 群号

        Returns:
            消息列表
        """
        return self.context_manager.get_context(group_id)

    def get_context_text(self, group_id: str) -> str:
        """获取指定群的窗口内容（合并为文本）。

        Args:
            group_id: 群号

        Returns:
            合并后的消息文本
        """
        return self.context_manager.get_context_text(group_id)

    def is_group_enabled(self, group_id: str) -> bool:
        """检查群号是否在白名单中。

        如果 enabled_groups 为空列表，则允许所有群组。

        Args:
            group_id: 群号

        Returns:
            是否允许该群使用
        """
        enabled_groups = self.config.enabled_groups
        if not enabled_groups:
            return True
        return str(group_id) in [str(g) for g in enabled_groups]

    def clear_group(self, group_id: str):
        """清空指定群的窗口和计数器。

        Args:
            group_id: 群号
        """
        self.context_manager.clear_group(group_id)
        logger.debug(f"{LOG_PREFIX} 群 {group_id} 上下文已清空")

    def get_all_groups(self) -> list[str]:
        """获取所有有记录的群号。

        Returns:
            群号列表
        """
        return self.context_manager.get_all_groups()

    def get_group_stats(self, group_id: str) -> dict:
        """获取指定群的统计信息。

        Args:
            group_id: 群号

        Returns:
            包含窗口大小、消息数量、当前计数的字典
        """
        context = self.get_context(group_id)
        counter = self.context_manager.counters.get(group_id, 0)

        return {
            "group_id": group_id,
            "window_size": self.config.window_size,
            "message_count": len(context),
            "current_counter": counter,
            "trigger_interval": self.config.trigger_interval,
            "trigger_probability": self.config.trigger_probability,
        }

    def get_all_stats(self) -> dict[str, dict]:
        """获取所有群组的统计信息。

        Returns:
            群号到统计信息的映射字典
        """
        groups = self.get_all_groups()
        return {group_id: self.get_group_stats(group_id) for group_id in groups}
