"""处理器基类模块。

定义所有处理器的通用接口和基础功能。
"""

from abc import ABC, abstractmethod
from typing import Any

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from ..constants import LOG_PREFIX


class BaseHandler(ABC):
    """处理器抽象基类。

    所有具体处理器都应继承此类，实现 handle 方法。

    Attributes:
        name: 处理器名称
        enabled: 是否启用
    """

    def __init__(self, name: str, enabled: bool = True):
        """初始化处理器。

        Args:
            name: 处理器名称
            enabled: 是否启用，默认为 True
        """
        self.name = name
        self.enabled = enabled

    @abstractmethod
    async def handle(self, event: AstrMessageEvent, **kwargs) -> Any:
        """处理事件。

        Args:
            event: AstrBot 消息事件
            **kwargs: 额外参数

        Returns:
            处理结果
        """
        pass

    def is_enabled(self) -> bool:
        """检查处理器是否启用。

        Returns:
            是否启用
        """
        return self.enabled

    def enable(self):
        """启用处理器。"""
        self.enabled = True
        logger.debug(f"{LOG_PREFIX} 处理器 {self.name} 已启用")

    def disable(self):
        """禁用处理器。"""
        self.enabled = False
        logger.debug(f"{LOG_PREFIX} 处理器 {self.name} 已禁用")

    def log_debug(self, message: str):
        """记录调试日志。

        Args:
            message: 日志消息
        """
        logger.debug(f"{LOG_PREFIX} [{self.name}] {message}")

    def log_info(self, message: str):
        """记录信息日志。

        Args:
            message: 日志消息
        """
        logger.info(f"{LOG_PREFIX} [{self.name}] {message}")

    def log_warning(self, message: str):
        """记录警告日志。

        Args:
            message: 日志消息
        """
        logger.warning(f"{LOG_PREFIX} [{self.name}] {message}")

    def log_error(self, message: str):
        """记录错误日志。

        Args:
            message: 日志消息
        """
        logger.error(f"{LOG_PREFIX} [{self.name}] {message}")
