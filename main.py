"""自动表情包插件主模块。

基于群聊语境主动发送表情包的 AstrBot 插件。
"""

from astrbot.api import logger
from astrbot.api.all import *
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.event.filter import EventMessageType
from astrbot.api.star import Context, Star, register

from .backend.category_manager import CategoryManager
from .config import DEFAULT_CATEGORY_DESCRIPTIONS, MEMES_DATA_PATH
from .constants import LOG_PREFIX
from .core.config_manager import ConfigManager
from .core.context_analyzer import ContextAnalyzer
from .handlers.command_handler import CommandHandler
from .handlers.group_message_handler import GroupMessageHandler
from .init import init_plugin
from .services.group_context_service import GroupContextService
from .services.llm_service import LLMService
from .services.meme_service import MemeService
from .utils.common import load_json


@register("meme_auto", "anka", "anka - 自动表情包 - 基于群聊语境主动发送", "4.0")
class MemeAutoPlugin(Star):
    """自动表情包插件主类。

    负责初始化所有模块并协调它们之间的工作。

    Attributes:
        context: AstrBot 上下文
        config_manager: 配置管理器
        category_manager: 类别管理器
        group_context_service: 群组上下文服务
        meme_service: 表情包服务
        llm_service: LLM 服务
        context_analyzer: 语境分析器
        group_message_handler: 群消息处理器
        command_handler: 命令处理器
    """

    def __init__(self, context: Context, config: dict = None):
        """初始化插件。

        Args:
            context: AstrBot 上下文
            config: 插件配置字典
        """
        super().__init__(context)

        # 初始化插件
        if not init_plugin():
            raise RuntimeError("插件初始化失败")

        # 初始化配置管理器
        self.config_manager = ConfigManager(config or {})

        # 初始化类别管理器
        self.category_manager = CategoryManager()

        # 加载表情包类别映射
        category_mapping = load_json(MEMES_DATA_PATH, DEFAULT_CATEGORY_DESCRIPTIONS)

        # 获取配置
        basic_config = self.config_manager.get_basic_config()
        llm_config = self.config_manager.get_llm_config()

        # 初始化服务层
        self.group_context_service = GroupContextService(config=basic_config)
        self.meme_service = MemeService(
            convert_static_to_gif=basic_config.convert_static_to_gif
        )
        self.llm_service = LLMService(
            config=llm_config,
            context=context,
            category_mapping=category_mapping,
        )

        # 初始化语境分析器
        self.context_analyzer = ContextAnalyzer(
            astrbot_context=context,
            category_mapping=category_mapping,
            use_llm_analysis=llm_config.use_llm_analysis,
            system_prompt=llm_config.system_prompt,
            user_prompt=llm_config.user_prompt,
        )

        # 初始化处理器
        self.group_message_handler = GroupMessageHandler(
            config=basic_config,
            context_service=self.group_context_service,
            analyzer=self.context_analyzer,
            meme_service=self.meme_service,
        )
        self.command_handler = CommandHandler(
            category_manager=self.category_manager,
            meme_service=self.meme_service,
        )

        logger.info(
            f"{LOG_PREFIX} 插件已初始化，"
            f"窗口大小: {basic_config.window_size}, "
            f"触发间隔: {basic_config.trigger_interval}, "
            f"LLM分析: {llm_config.use_llm_analysis}"
        )

    @filter.event_message_type(EventMessageType.GROUP_MESSAGE)
    async def on_group_message(self, event: AstrMessageEvent):
        """处理群消息事件。

        Args:
            event: AstrBot 消息事件
        """
        await self.group_message_handler.handle(event)

    @filter.command_group("表情管理")
    def meme_auto(self):
        """表情包管理命令组。

        可用命令:
        - 查看图库: 查看所有可用表情包类别
        - 添加表情: 上传表情包到指定类别
        - 图库统计: 显示图库详细统计信息
        """
        pass

    @meme_auto.command("查看图库")
    async def list_emotions(self, event: AstrMessageEvent):
        """查看所有可用表情包类别。"""
        async for result in self.command_handler.list_emotions(event):
            yield result

    @filter.permission_type(filter.PermissionType.ADMIN)
    @meme_auto.command("添加表情")
    async def upload_meme(self, event: AstrMessageEvent, category: str = None):
        """上传表情包到指定类别。

        Args:
            event: AstrBot 消息事件
            category: 目标类别名称
        """
        async for result in self.command_handler.upload_meme(event, category):
            yield result

    @filter.event_message_type(EventMessageType.ALL)
    async def handle_upload_image(self, event: AstrMessageEvent):
        """处理用户上传的图片。"""
        async for result in self.command_handler.handle_upload_image(event):
            yield result

    @meme_auto.command("图库统计")
    async def show_library_stats(self, event: AstrMessageEvent):
        """显示图库详细统计信息。"""
        async for result in self.command_handler.show_stats(event):
            yield result

    async def terminate(self):
        """清理资源。"""
        logger.info(f"{LOG_PREFIX} 插件已关闭")
