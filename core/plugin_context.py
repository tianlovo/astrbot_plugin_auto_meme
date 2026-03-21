"""插件上下文模块。

管理插件全局状态，如上传状态等。
"""

import time
from typing import Any

from astrbot.api import logger

from ..constants import LOG_PREFIX
from ..models import UploadState


class PluginContext:
    """插件上下文类。

    管理插件的全局状态，包括用户上传状态、临时数据等。
    提供线程安全的状态管理方法。

    Attributes:
        _upload_states: 用户上传状态映射 {user_key: UploadState}
        _metadata: 插件元数据存储
    """

    def __init__(self):
        """初始化插件上下文。"""
        self._upload_states: dict[str, UploadState] = {}
        self._metadata: dict[str, Any] = {}

        logger.info(f"{LOG_PREFIX} 插件上下文已初始化")

    # ==================== 上传状态管理 ====================

    def set_upload_state(
        self,
        session_id: str,
        sender_id: str,
        category: str,
        expire_seconds: float = 30.0,
    ) -> UploadState:
        """设置用户上传状态。

        Args:
            session_id: 会话ID
            sender_id: 发送者ID
            category: 目标类别
            expire_seconds: 过期时间（秒），默认30秒

        Returns:
            UploadState: 创建的上传状态对象
        """
        user_key = f"{session_id}_{sender_id}"
        expire_time = time.time() + expire_seconds

        upload_state = UploadState(
            category=category,
            expire_time=expire_time,
        )
        self._upload_states[user_key] = upload_state

        logger.debug(
            f"{LOG_PREFIX} 设置上传状态: user_key={user_key}, category={category}, "
            f"expire_in={expire_seconds}s"
        )
        return upload_state

    def get_upload_state(self, session_id: str, sender_id: str) -> UploadState | None:
        """获取用户上传状态。

        如果状态已过期，会自动清理并返回 None。

        Args:
            session_id: 会话ID
            sender_id: 发送者ID

        Returns:
            UploadState | None: 上传状态对象，如果不存在或已过期则返回 None
        """
        user_key = f"{session_id}_{sender_id}"
        upload_state = self._upload_states.get(user_key)

        if upload_state is None:
            return None

        # 检查是否过期
        if time.time() > upload_state.expire_time:
            logger.debug(f"{LOG_PREFIX} 上传状态已过期: user_key={user_key}")
            self.remove_upload_state(session_id, sender_id)
            return None

        return upload_state

    def remove_upload_state(self, session_id: str, sender_id: str) -> bool:
        """移除用户上传状态。

        Args:
            session_id: 会话ID
            sender_id: 发送者ID

        Returns:
            bool: 是否成功移除
        """
        user_key = f"{session_id}_{sender_id}"

        if user_key in self._upload_states:
            del self._upload_states[user_key]
            logger.debug(f"{LOG_PREFIX} 移除上传状态: user_key={user_key}")
            return True

        return False

    def clear_expired_upload_states(self) -> int:
        """清理所有过期的上传状态。

        Returns:
            int: 清理的状态数量
        """
        current_time = time.time()
        expired_keys = [
            key
            for key, state in self._upload_states.items()
            if current_time > state.expire_time
        ]

        for key in expired_keys:
            del self._upload_states[key]

        if expired_keys:
            logger.debug(f"{LOG_PREFIX} 清理 {len(expired_keys)} 个过期上传状态")

        return len(expired_keys)

    def has_active_upload_state(self, session_id: str, sender_id: str) -> bool:
        """检查用户是否有活跃的上传状态。

        Args:
            session_id: 会话ID
            sender_id: 发送者ID

        Returns:
            bool: 是否有活跃的上传状态
        """
        return self.get_upload_state(session_id, sender_id) is not None

    def get_all_upload_states(self) -> dict[str, UploadState]:
        """获取所有上传状态（包括已过期的）。

        Returns:
            dict: 用户键到上传状态的映射副本
        """
        return self._upload_states.copy()

    def clear_all_upload_states(self) -> int:
        """清空所有上传状态。

        Returns:
            int: 清理的状态数量
        """
        count = len(self._upload_states)
        self._upload_states.clear()

        if count > 0:
            logger.info(f"{LOG_PREFIX} 清空所有上传状态: {count} 个")

        return count

    # ==================== 元数据管理 ====================

    def set_metadata(self, key: str, value: Any) -> None:
        """设置元数据。

        Args:
            key: 元数据键
            value: 元数据值
        """
        self._metadata[key] = value
        logger.debug(f"{LOG_PREFIX} 设置元数据: {key}")

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """获取元数据。

        Args:
            key: 元数据键
            default: 默认值，如果键不存在则返回此值

        Returns:
            Any: 元数据值或默认值
        """
        return self._metadata.get(key, default)

    def remove_metadata(self, key: str) -> bool:
        """移除元数据。

        Args:
            key: 元数据键

        Returns:
            bool: 是否成功移除
        """
        if key in self._metadata:
            del self._metadata[key]
            logger.debug(f"{LOG_PREFIX} 移除元数据: {key}")
            return True
        return False

    def clear_all_metadata(self) -> int:
        """清空所有元数据。

        Returns:
            int: 清理的元数据数量
        """
        count = len(self._metadata)
        self._metadata.clear()

        if count > 0:
            logger.debug(f"{LOG_PREFIX} 清空所有元数据: {count} 个")

        return count

    # ==================== 统计信息 ====================

    def get_stats(self) -> dict[str, Any]:
        """获取插件上下文的统计信息。

        Returns:
            dict: 统计信息字典
        """
        current_time = time.time()
        active_uploads = sum(
            1
            for state in self._upload_states.values()
            if current_time <= state.expire_time
        )
        expired_uploads = len(self._upload_states) - active_uploads

        return {
            "upload_states": {
                "total": len(self._upload_states),
                "active": active_uploads,
                "expired": expired_uploads,
            },
            "metadata_count": len(self._metadata),
        }

    def cleanup(self) -> None:
        """清理所有资源。

        在插件终止时调用，清理所有状态和元数据。
        """
        upload_count = len(self._upload_states)
        metadata_count = len(self._metadata)

        self._upload_states.clear()
        self._metadata.clear()

        logger.info(
            f"{LOG_PREFIX} 插件上下文已清理: "
            f"upload_states={upload_count}, metadata={metadata_count}"
        )
