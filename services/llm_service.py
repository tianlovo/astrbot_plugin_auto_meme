"""LLM 服务模块。

封装 LLM 调用逻辑和语境分析功能。
"""

import random
import re

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent
from astrbot.api.star import Context

from ..constants import (
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_USER_PROMPT,
    EMOTION_KEYWORDS,
    LOG_PREFIX,
)
from ..models import LLMConfig


class LLMService:
    """LLM 服务类。

    负责调用 LLM 分析群聊语境，选择合适的表情包类别。

    Attributes:
        config: LLM 配置
        context: AstrBot 上下文
        category_mapping: 类别映射字典
    """

    def __init__(
        self, config: LLMConfig, context: Context, category_mapping: dict[str, str]
    ):
        """初始化 LLM 服务。

        Args:
            config: LLM 配置对象
            context: AstrBot 上下文
            category_mapping: 类别名称到描述的映射
        """
        self.config = config
        self.context = context
        self.category_mapping = category_mapping
        logger.debug(
            f"{LOG_PREFIX} LLM 服务已初始化，使用 LLM 分析: {config.use_llm_analysis}"
        )

    async def analyze_context(
        self, messages: list[str], event: AstrMessageEvent
    ) -> str:
        """分析语境，返回最合适的表情包类别。

        根据配置决定是否使用 LLM 分析，否则使用关键词分析。

        Args:
            messages: 消息列表
            event: 消息事件对象

        Returns:
            表情包类别名称
        """
        if self.config.use_llm_analysis:
            return await self._analyze_by_llm(messages, event)
        else:
            return self._analyze_by_keywords(messages)

    async def _analyze_by_llm(
        self, messages: list[str], event: AstrMessageEvent
    ) -> str:
        """使用 LLM 分析语境。

        Args:
            messages: 消息列表
            event: 消息事件对象

        Returns:
            表情包类别名称
        """
        if not messages:
            return self._get_random_emotion()

        context_text = "\n".join(messages)
        available_emotions = list(self.category_mapping.keys())
        emotions_list = ", ".join(available_emotions)

        # 构建系统提示词
        if self.config.system_prompt:
            system_prompt = self.config.system_prompt.format(
                emotions_list=emotions_list
            )
        else:
            system_prompt = DEFAULT_SYSTEM_PROMPT.format(emotions_list=emotions_list)

        # 构建用户提示词
        if self.config.user_prompt:
            user_prompt = self.config.user_prompt.format(context_text=context_text)
        else:
            user_prompt = DEFAULT_USER_PROMPT.format(context_text=context_text)

        # 如果开启调试模式，打印完整提示词
        if self.config.debug_prompt:
            logger.info(f"{LOG_PREFIX} 🔍 [调试模式] 完整系统提示词:\n{'='*50}\n{system_prompt}\n{'='*50}")
            logger.info(f"{LOG_PREFIX} 🔍 [调试模式] 完整用户提示词:\n{'='*50}\n{user_prompt}\n{'='*50}")

        try:
            provider_id = await self._get_provider_id(event)
            if not provider_id:
                logger.warning(f"{LOG_PREFIX} 无法获取 LLM provider ID，使用关键词分析")
                return self._analyze_by_keywords(messages)

            llm_resp = await self.context.llm_generate(
                chat_provider_id=provider_id,
                prompt=user_prompt,
                system_prompt=system_prompt,
            )

            result = llm_resp.completion_text.strip().lower()
            result = re.sub(r"[^\w]", "", result)

            if result == "random" or result not in available_emotions:
                logger.debug(f"{LOG_PREFIX} LLM 返回无效类别 '{result}'，随机选择")
                return self._get_random_emotion()

            logger.info(f"{LOG_PREFIX} LLM 分析结果: {result}")
            return result

        except Exception as e:
            logger.error(f"{LOG_PREFIX} LLM 分析失败: {e}")
            return self._analyze_by_keywords(messages)

    def _analyze_by_keywords(self, messages: list[str]) -> str:
        """基于关键词分析语境。

        Args:
            messages: 消息列表

        Returns:
            表情包类别名称
        """
        if not messages:
            return self._get_random_emotion()

        context_text = "\n".join(messages)
        available_emotions = list(self.category_mapping.keys())

        # 统计每个类别的关键词匹配次数
        scores = {}
        for emotion, keywords in EMOTION_KEYWORDS.items():
            if emotion not in available_emotions:
                continue
            score = 0
            for keyword in keywords:
                count = len(re.findall(re.escape(keyword), context_text, re.IGNORECASE))
                score += count
            if score > 0:
                scores[emotion] = score

        if not scores:
            return self._get_random_emotion()

        max_score = max(scores.values())
        best_emotions = [e for e, s in scores.items() if s == max_score]
        selected = random.choice(best_emotions)
        logger.debug(f"{LOG_PREFIX} 关键词分析结果: {selected} (得分: {max_score})")
        return selected

    async def _get_provider_id(self, event: AstrMessageEvent) -> str | None:
        """获取 LLM Provider ID。

        优先使用配置的 Provider ID，如果未配置或无效则使用当前会话的 Provider。

        Args:
            event: 消息事件对象

        Returns:
            Provider ID 或 None
        """
        # 如果配置了特定的 Provider ID，先尝试使用它
        if self.config.llm_provider_id:
            # 检查配置的 Provider 是否存在
            provider = self.context.get_provider_by_id(self.config.llm_provider_id)
            if provider:
                logger.debug(f"{LOG_PREFIX} 使用配置的 Provider: {self.config.llm_provider_id}")
                return self.config.llm_provider_id
            else:
                logger.warning(
                    f"{LOG_PREFIX} 配置的 Provider '{self.config.llm_provider_id}' 不存在，"
                    f"将尝试使用当前会话的 Provider"
                )

        # 回退到当前会话的 Provider
        try:
            umo = event.unified_msg_origin
            provider_id = await self.context.get_current_chat_provider_id(umo=umo)
            return provider_id
        except Exception as e:
            logger.warning(f"{LOG_PREFIX} 获取当前会话 Provider ID 失败: {e}")
            return None

    def _get_random_emotion(self) -> str:
        """获取随机表情包类别。

        Returns:
            随机类别名称
        """
        available_emotions = list(self.category_mapping.keys())
        if not available_emotions:
            logger.warning(f"{LOG_PREFIX} 没有可用的表情包类别")
            return "happy"  # 默认返回 happy
        return random.choice(available_emotions)

    def update_category_mapping(self, category_mapping: dict[str, str]):
        """更新类别映射。

        Args:
            category_mapping: 新的类别映射字典
        """
        self.category_mapping = category_mapping
        logger.debug(f"{LOG_PREFIX} 类别映射已更新，共 {len(category_mapping)} 个类别")

    def get_available_emotions(self) -> list[str]:
        """获取所有可用的表情包类别。

        Returns:
            类别名称列表
        """
        return list(self.category_mapping.keys())
