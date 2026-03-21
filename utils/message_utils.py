"""消息处理工具模块。

提供消息格式化和组件处理相关的工具函数。
"""

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from ..constants import LOG_PREFIX, MESSAGE_TYPE_MAP


class MessageUtils:
    """消息处理工具类。

    提供将消息组件格式化为文本的静态方法。
    """

    @staticmethod
    def format_message(event: AstrMessageEvent) -> str:
        """将消息事件格式化为文本表示。

        遍历消息中的所有组件，根据组件类型使用 MESSAGE_TYPE_MAP 进行转换，
        将消息组件转换为可读的文本格式。

        Args:
            event: AstrBot 消息事件对象，包含消息组件信息。

        Returns:
            格式化后的消息文本，各组件文本以空格连接。
            如果消息为空或无法格式化，返回空字符串。

        Example:
            >>> text = MessageUtils.format_message(event)
            >>> print(text)
            'Hello [图片] [@用户]'
        """
        if not event or not event.message_obj or not event.message_obj.message:
            return ""

        parts = []
        for component in event.message_obj.message:
            comp_type = type(component).__name__

            if comp_type in MESSAGE_TYPE_MAP:
                try:
                    text = MESSAGE_TYPE_MAP[comp_type](component)
                    if text:
                        parts.append(text)
                except Exception as e:
                    logger.warning(f"{LOG_PREFIX} 处理消息组件 {comp_type} 失败: {e}")
            elif hasattr(component, "text"):
                text = component.text
                if text:
                    parts.append(text)

        return " ".join(parts)

    @staticmethod
    def get_message_components(event: AstrMessageEvent) -> list:
        """获取消息中的所有组件类型列表。

        Args:
            event: AstrBot 消息事件对象。

        Returns:
            消息组件类型名称列表。
        """
        if not event or not event.message_obj or not event.message_obj.message:
            return []

        return [type(component).__name__ for component in event.message_obj.message]

    @staticmethod
    def has_component_type(event: AstrMessageEvent, component_type: str) -> bool:
        """检查消息是否包含指定类型的组件。

        Args:
            event: AstrBot 消息事件对象。
            component_type: 要检查的组件类型名称（如 "Image", "Plain" 等）。

        Returns:
            如果消息包含指定类型的组件则返回 True，否则返回 False。
        """
        if not event or not event.message_obj or not event.message_obj.message:
            return False

        return any(
            type(component).__name__ == component_type
            for component in event.message_obj.message
        )

    @staticmethod
    def extract_images(event: AstrMessageEvent) -> list:
        """从消息中提取所有图片组件。

        Args:
            event: AstrBot 消息事件对象。

        Returns:
            图片组件列表。
        """
        if not event or not event.message_obj or not event.message_obj.message:
            return []

        from astrbot.api.message_components import Image

        return [
            component
            for component in event.message_obj.message
            if isinstance(component, Image)
        ]
