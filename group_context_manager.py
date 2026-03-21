"""群组上下文管理器 - 管理群聊消息的滑动窗口"""

from collections import deque


class GroupContextManager:
    """管理群组消息的滑动窗口和触发计数器"""

    def __init__(self, window_size: int = 30):
        """
        初始化群组上下文管理器

        Args:
            window_size: 滑动窗口大小，默认30条消息
        """
        self.window_size = window_size
        self.windows: dict[str, deque] = {}  # {group_id: deque([messages])}
        self.counters: dict[str, int] = {}  # {group_id: count}
        self.processing: dict[str, bool] = {}  # {group_id: is_processing} 防止重复触发

    def add_message(self, group_id: str, message: str) -> int:
        """
        添加消息到指定群的滑动窗口

        Args:
            group_id: 群号
            message: 消息内容

        Returns:
            当前消息计数
        """
        if group_id not in self.windows:
            self.windows[group_id] = deque(maxlen=self.window_size)
            self.counters[group_id] = 0

        self.windows[group_id].append(message)
        self.counters[group_id] += 1

        return self.counters[group_id]

    def should_trigger(self, group_id: str, interval: int) -> bool:
        """
        判断是否应触发表情包发送

        Args:
            group_id: 群号
            interval: 触发间隔（消息数）

        Returns:
            是否应触发
        """
        if group_id not in self.counters:
            return False

        # 如果正在处理中（LLM分析或发送表情包），不触发
        if self.processing.get(group_id, False):
            return False

        return self.counters[group_id] >= interval

    def set_processing(self, group_id: str, processing: bool):
        """
        设置群的处理状态

        Args:
            group_id: 群号
            processing: 是否正在处理中
        """
        self.processing[group_id] = processing

    def is_processing(self, group_id: str) -> bool:
        """
        检查群是否正在处理中

        Args:
            group_id: 群号

        Returns:
            是否正在处理中
        """
        return self.processing.get(group_id, False)

    def reset_counter(self, group_id: str):
        """
        重置指定群的消息计数器

        Args:
            group_id: 群号
        """
        if group_id in self.counters:
            self.counters[group_id] = 0

    def get_context(self, group_id: str) -> list[str]:
        """
        获取指定群的窗口内容

        Args:
            group_id: 群号

        Returns:
            消息列表
        """
        if group_id not in self.windows:
            return []

        return list(self.windows[group_id])

    def get_context_text(self, group_id: str) -> str:
        """
        获取指定群的窗口内容（合并为文本）

        Args:
            group_id: 群号

        Returns:
            合并后的消息文本
        """
        messages = self.get_context(group_id)
        return "\n".join(messages)

    def clear_group(self, group_id: str):
        """
        清空指定群的窗口和计数器

        Args:
            group_id: 群号
        """
        if group_id in self.windows:
            del self.windows[group_id]
        if group_id in self.counters:
            del self.counters[group_id]
        if group_id in self.processing:
            del self.processing[group_id]

    def get_all_groups(self) -> list[str]:
        """
        获取所有有记录的群号

        Returns:
            群号列表
        """
        return list(self.windows.keys())
