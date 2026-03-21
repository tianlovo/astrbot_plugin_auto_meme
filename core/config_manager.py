"""配置管理器模块。

封装配置读取逻辑，支持父级结构（basic 和 llm_analysis），
提供配置热重载功能。
"""

from typing import Any

from astrbot.api import logger

from ..constants import LOG_PREFIX
from ..types import BasicConfig, LLMConfig, WebUIConfig


class ConfigManager:
    """配置管理器类。

    负责管理插件的配置，支持从父级结构（basic、llm_analysis、webui）读取配置，
    并提供配置热重载功能。

    Attributes:
        _raw_config: 原始配置字典
        _basic_config: 基础配置对象
        _llm_config: LLM配置对象
        _webui_config: WebUI配置对象
    """

    def __init__(self, config: dict[str, Any] | None = None):
        """初始化配置管理器。

        Args:
            config: 原始配置字典，如果为None则使用空字典
        """
        self._raw_config = config or {}
        self._basic_config: BasicConfig | None = None
        self._llm_config: LLMConfig | None = None
        self._webui_config: WebUIConfig | None = None

        self._parse_config()
        logger.info(f"{LOG_PREFIX} 配置管理器已初始化")

    def _parse_config(self) -> None:
        """解析原始配置，提取基础配置、LLM配置和WebUI配置。"""
        try:
            # 解析基础配置（basic 父级结构）
            basic_dict = self._raw_config.get("basic", {})
            self._basic_config = BasicConfig.from_dict(basic_dict)

            # 解析LLM配置（llm_analysis 父级结构）
            llm_dict = self._raw_config.get("llm_analysis", {})
            self._llm_config = LLMConfig.from_dict(llm_dict)

            # 解析WebUI配置（webui 父级结构）
            webui_dict = self._raw_config.get("webui", {})
            self._webui_config = WebUIConfig.from_dict(webui_dict)

        except Exception as e:
            logger.error(f"{LOG_PREFIX} 配置解析失败: {e}")
            # 使用默认配置作为回退
            self._basic_config = BasicConfig.from_dict({})
            self._llm_config = LLMConfig.from_dict({})
            self._webui_config = WebUIConfig.from_dict({})

    def reload_config(self, new_config: dict[str, Any] | None = None) -> None:
        """热重载配置。

        重新解析配置，如果提供了新配置则使用新配置，
        否则重新解析当前配置。

        Args:
            new_config: 新的配置字典，如果为None则重新解析当前配置
        """
        if new_config is not None:
            self._raw_config = new_config

        old_basic = self._basic_config
        old_llm = self._llm_config
        old_webui = self._webui_config

        try:
            self._parse_config()
            logger.info(f"{LOG_PREFIX} 配置已热重载")

            # 记录配置变更
            if old_basic and old_basic != self._basic_config:
                logger.debug(f"{LOG_PREFIX} 基础配置已更新")
            if old_llm and old_llm != self._llm_config:
                logger.debug(f"{LOG_PREFIX} LLM配置已更新")
            if old_webui and old_webui != self._webui_config:
                logger.debug(f"{LOG_PREFIX} WebUI配置已更新")

        except Exception as e:
            logger.error(f"{LOG_PREFIX} 配置热重载失败: {e}")
            # 保持原有配置不变
            self._basic_config = old_basic
            self._llm_config = old_llm
            self._webui_config = old_webui

    def get_basic_config(self) -> BasicConfig:
        """获取基础配置。

        Returns:
            BasicConfig: 基础配置对象

        Raises:
            RuntimeError: 如果配置未初始化
        """
        if self._basic_config is None:
            raise RuntimeError(f"{LOG_PREFIX} 基础配置未初始化")
        return self._basic_config

    def get_llm_config(self) -> LLMConfig:
        """获取LLM配置。

        Returns:
            LLMConfig: LLM配置对象

        Raises:
            RuntimeError: 如果配置未初始化
        """
        if self._llm_config is None:
            raise RuntimeError(f"{LOG_PREFIX} LLM配置未初始化")
        return self._llm_config

    def get_webui_config(self) -> WebUIConfig:
        """获取WebUI配置。

        Returns:
            WebUIConfig: WebUI配置对象

        Raises:
            RuntimeError: 如果配置未初始化
        """
        if self._webui_config is None:
            raise RuntimeError(f"{LOG_PREFIX} WebUI配置未初始化")
        return self._webui_config

    def get_raw_config(self) -> dict[str, Any]:
        """获取原始配置字典。

        Returns:
            dict: 原始配置字典的副本
        """
        return self._raw_config.copy()

    def update_basic_config(self, **kwargs) -> None:
        """更新基础配置的特定字段。

        Args:
            **kwargs: 要更新的字段和值

        Raises:
            RuntimeError: 如果配置未初始化
            AttributeError: 如果字段不存在
        """
        if self._basic_config is None:
            raise RuntimeError(f"{LOG_PREFIX} 基础配置未初始化")

        for key, value in kwargs.items():
            if not hasattr(self._basic_config, key):
                raise AttributeError(f"{LOG_PREFIX} BasicConfig 没有属性: {key}")
            setattr(self._basic_config, key, value)

        logger.debug(f"{LOG_PREFIX} 基础配置已更新: {list(kwargs.keys())}")

    def update_llm_config(self, **kwargs) -> None:
        """更新LLM配置的特定字段。

        Args:
            **kwargs: 要更新的字段和值

        Raises:
            RuntimeError: 如果配置未初始化
            AttributeError: 如果字段不存在
        """
        if self._llm_config is None:
            raise RuntimeError(f"{LOG_PREFIX} LLM配置未初始化")

        for key, value in kwargs.items():
            if not hasattr(self._llm_config, key):
                raise AttributeError(f"{LOG_PREFIX} LLMConfig 没有属性: {key}")
            setattr(self._llm_config, key, value)

        logger.debug(f"{LOG_PREFIX} LLM配置已更新: {list(kwargs.keys())}")

    def is_group_enabled(self, group_id: str) -> bool:
        """检查群号是否在白名单中。

        Args:
            group_id: 群号

        Returns:
            bool: 如果白名单为空则返回True，否则检查群号是否在列表中
        """
        config = self.get_basic_config()
        if not config.enabled_groups:
            return True
        return str(group_id) in [str(g) for g in config.enabled_groups]
