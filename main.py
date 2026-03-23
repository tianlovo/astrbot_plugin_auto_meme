"""自动表情包插件主模块。

基于群聊语境主动发送表情包的 AstrBot 插件。
"""

import asyncio

from astrbot.api import logger
from astrbot.api.all import *
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.event.filter import EventMessageType
from astrbot.api.star import Context, Star, register

from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import AiocqhttpMessageEvent

from .backend.category_manager import CategoryManager
from .config import DEFAULT_CATEGORY_DESCRIPTIONS, MEMES_DIR, MEMES_DATA_PATH
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
from .webui import start_server


@register("meme_auto", "anka", "anka - 自动表情包 - 基于群聊语境主动发送", "4.1.5")
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
        webui_task: WebUI 后台任务
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
            convert_static_to_gif=basic_config.convert_static_to_gif,
            timezone=basic_config.timezone
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
            timezone=basic_config.timezone,
            llm_provider_id=llm_config.llm_provider_id,
            debug_prompt=llm_config.debug_prompt
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

        # 获取 WebUI 配置并初始化
        webui_config = self.config_manager.get_webui_config()
        self.webui_task = None
        self._init_webui(webui_config.webui_port, webui_config.webui_key)

        logger.info(
            f"{LOG_PREFIX} 插件已初始化，"
            f"窗口大小: {basic_config.window_size}, "
            f"触发间隔: {basic_config.trigger_interval}, "
            f"LLM分析: {llm_config.use_llm_analysis}"
        )
        logger.info(
            f"{LOG_PREFIX} 消息监听已启动 - 使用 EventMessageType.ALL 过滤器"
        )

    def _init_webui(self, port: int, key: str):
        """初始化 WebUI 服务。

        Args:
            port: WebUI 端口号
            key: WebUI 登录密钥
        """
        try:
            # 准备 WebUI 配置
            webui_config = {
                "webui_port": port,
                "server_key": key,
                "category_manager": self.category_manager,
            }

            # 启动 WebUI 服务
            self.webui_task = asyncio.create_task(start_server(webui_config))
            logger.info(f"{LOG_PREFIX} WebUI 服务已启动，访问地址: http://localhost:{port}")
        except Exception as e:
            logger.error(f"{LOG_PREFIX} WebUI 服务启动失败: {e}")

    @filter.event_message_type(EventMessageType.ALL)
    async def on_all_message(self, event: AstrMessageEvent):
        """处理所有消息事件。

        捕获所有消息，过滤出 aiocqhttp 平台的群消息进行处理。

        Args:
            event: AstrBot 消息事件
        """
        # 只处理群消息
        if not event.get_group_id():
            return

        # 处理群消息
        await self.group_message_handler.handle(event)

    async def terminate(self):
        """清理资源。"""
        # 关闭 WebUI 服务
        if self.webui_task:
            self.webui_task.cancel()
            try:
                await self.webui_task
            except asyncio.CancelledError:
                pass
            logger.info(f"{LOG_PREFIX} WebUI 服务已关闭")

        logger.info(f"{LOG_PREFIX} 插件已关闭")
