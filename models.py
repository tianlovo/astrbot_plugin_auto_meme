"""类型定义模块。

包含插件中使用的所有数据类型和配置类。
"""

from dataclasses import dataclass


@dataclass
class BasicConfig:
    """基础配置数据类。

    Attributes:
        enabled_groups: 启用的QQ群列表
        window_size: 滑动窗口大小
        trigger_interval: 触发间隔（消息数）
        trigger_probability: 触发概率
        convert_static_to_gif: 是否将静态图转为GIF
        timezone: 时区设置
    """

    enabled_groups: list[str]
    window_size: int
    trigger_interval: int
    trigger_probability: int
    convert_static_to_gif: bool
    timezone: str

    @classmethod
    def from_dict(cls, config: dict) -> "BasicConfig":
        """从字典创建配置对象。

        Args:
            config: 配置字典

        Returns:
            BasicConfig实例
        """
        return cls(
            enabled_groups=config.get("enabled_groups", []),
            window_size=config.get("window_size", 30),
            trigger_interval=config.get("trigger_interval", 5),
            trigger_probability=config.get("trigger_probability", 50),
            convert_static_to_gif=config.get("convert_static_to_gif", False),
            timezone=config.get("timezone", "Asia/Shanghai"),
        )


@dataclass
class WebUIConfig:
    """WebUI配置数据类。

    Attributes:
        webui_port: WebUI 端口号
        webui_key: WebUI 登录密钥
    """

    webui_port: int
    webui_key: str

    @classmethod
    def from_dict(cls, config: dict) -> "WebUIConfig":
        """从字典创建配置对象。

        Args:
            config: 配置字典

        Returns:
            WebUIConfig实例
        """
        return cls(
            webui_port=config.get("webui_port", 5000),
            webui_key=config.get("webui_key", "meme_auto"),
        )


@dataclass
class LLMConfig:
    """LLM配置数据类。

    Attributes:
        use_llm_analysis: 是否使用LLM分析语境
        system_prompt: 自定义系统提示词
        user_prompt: 自定义用户提示词
        llm_provider_id: LLM Provider ID，为空则使用当前会话的Provider
        debug_prompt: 是否打印完整提示词到日志
    """

    use_llm_analysis: bool
    system_prompt: str
    user_prompt: str
    llm_provider_id: str
    debug_prompt: bool

    @classmethod
    def from_dict(cls, config: dict) -> "LLMConfig":
        """从字典创建配置对象。

        Args:
            config: 配置字典

        Returns:
            LLMConfig实例
        """
        return cls(
            use_llm_analysis=config.get("use_llm_analysis", True),
            system_prompt=config.get("llm_system_prompt", ""),
            user_prompt=config.get("llm_user_prompt", ""),
            llm_provider_id=config.get("llm_provider_id", ""),
            debug_prompt=config.get("debug_prompt", False),
        )


@dataclass
class MemeInfo:
    """表情包信息数据类。

    Attributes:
        emotion: 表情包类别
        filename: 文件名
        path: 完整路径
    """

    emotion: str
    filename: str
    path: str


@dataclass
class UploadState:
    """上传状态数据类。

    Attributes:
        category: 目标类别
        expire_time: 过期时间戳
    """

    category: str
    expire_time: float
