"""语境分析器模块。

封装关键词分析和 LLM 分析两种策略，根据配置自动选择策略。
"""

import random
import re
from typing import TYPE_CHECKING

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from ..constants import (
    DEFAULT_SYSTEM_PROMPT,
    DEFAULT_USER_PROMPT,
    EMOTION_KEYWORDS,
    LOG_PREFIX,
)

if TYPE_CHECKING:
    from astrbot.api.star import Context


class ContextAnalyzer:
    """语境分析器类。

    提供关键词分析和 LLM 分析两种策略，根据配置自动选择策略
    来分析群聊语境并返回最合适的表情包类别。

    Attributes:
        _astrbot_context: AstrBot 上下文对象
        _category_mapping: 表情包类别映射
        _use_llm_analysis: 是否使用 LLM 分析
        _system_prompt: 自定义系统提示词
        _user_prompt: 自定义用户提示词
    """

    def __init__(
        self,
        astrbot_context: "Context",
        category_mapping: dict[str, str],
        use_llm_analysis: bool = True,
        system_prompt: str = "",
        user_prompt: str = "",
    ):
        """初始化语境分析器。

        Args:
            astrbot_context: AstrBot 上下文对象，用于调用 LLM
            category_mapping: 表情包类别映射 {类别名: 描述}
            use_llm_analysis: 是否使用 LLM 分析，默认为 True
            system_prompt: 自定义系统提示词，为空则使用默认提示词
            user_prompt: 自定义用户提示词，为空则使用默认提示词
        """
        self._astrbot_context = astrbot_context
        self._category_mapping = category_mapping
        self._use_llm_analysis = use_llm_analysis
        self._system_prompt = system_prompt
        self._user_prompt = user_prompt

        logger.info(
            f"{LOG_PREFIX} 语境分析器已初始化，使用策略: {'LLM' if use_llm_analysis else '关键词'}"
        )

    async def analyze(self, event: AstrMessageEvent, messages: list[str]) -> str:
        """分析语境，返回最合适的表情包类别。

        根据配置自动选择 LLM 分析或关键词分析策略。

        Args:
            event: 消息事件对象，用于获取 provider ID
            messages: 消息列表

        Returns:
            str: 表情包类别名称
        """
        if self._use_llm_analysis:
            return await self._analyze_by_llm(event, messages)
        else:
            return self._analyze_by_keywords(messages)

    def _analyze_by_keywords(self, messages: list[str]) -> str:
        """基于关键词分析语境。

        统计消息中各情绪类别的关键词匹配次数，返回得分最高的类别。
        如果没有匹配到关键词，则随机选择。

        Args:
            messages: 消息列表

        Returns:
            str: 表情包类别名称
        """
        if not messages:
            return random.choice(list(self._category_mapping.keys()))

        # 合并所有消息文本
        context_text = "\n".join(messages)

        # 统计每个类别的关键词匹配次数
        scores: dict[str, int] = {}
        for emotion, keywords in EMOTION_KEYWORDS.items():
            if emotion not in self._category_mapping:
                continue
            score = 0
            for keyword in keywords:
                count = len(re.findall(re.escape(keyword), context_text, re.IGNORECASE))
                score += count
            if score > 0:
                scores[emotion] = score

        if not scores:
            # 没有匹配到关键词，随机选择
            logger.debug(f"{LOG_PREFIX} 关键词分析未匹配，随机选择类别")
            return random.choice(list(self._category_mapping.keys()))

        # 选择得分最高的类别
        max_score = max(scores.values())
        best_emotions = [e for e, s in scores.items() if s == max_score]
        selected = random.choice(best_emotions)

        logger.debug(f"{LOG_PREFIX} 关键词分析结果: {selected} (得分: {max_score})")
        return selected

    async def _analyze_by_llm(
        self, event: AstrMessageEvent, messages: list[str]
    ) -> str:
        """使用 LLM 分析语境。

        调用 AstrBot 的 LLM 接口分析群聊消息，返回最合适的表情包类别。
        如果 LLM 分析失败，则回退到关键词分析。

        Args:
            event: 消息事件对象，用于获取 provider ID
            messages: 消息列表

        Returns:
            str: 表情包类别名称
        """
        if not messages:
            return random.choice(list(self._category_mapping.keys()))

        # 合并所有消息文本
        context_text = "\n".join(messages)

        # 构建可用的表情包类别列表
        available_emotions = list(self._category_mapping.keys())
        emotions_list = ", ".join(available_emotions)

        # 构建系统提示词
        if self._system_prompt:
            system_prompt = self._system_prompt.format(emotions_list=emotions_list)
        else:
            system_prompt = DEFAULT_SYSTEM_PROMPT.format(emotions_list=emotions_list)

        # 构建用户提示词
        if self._user_prompt:
            user_prompt = self._user_prompt.format(context_text=context_text)
        else:
            user_prompt = DEFAULT_USER_PROMPT.format(context_text=context_text)

        try:
            # 获取当前会话的 Provider ID
            umo = event.unified_msg_origin
            provider_id = await self._astrbot_context.get_current_chat_provider_id(
                umo=umo
            )

            if not provider_id:
                logger.warning(f"{LOG_PREFIX} 无法获取 LLM provider ID，使用关键词分析")
                return self._analyze_by_keywords(messages)

            # 调用 LLM
            llm_resp = await self._astrbot_context.llm_generate(
                chat_provider_id=provider_id,
                prompt=user_prompt,
                system_prompt=system_prompt,
            )

            # 解析 LLM 响应
            result = llm_resp.completion_text.strip().lower()

            # 清理结果，只保留类别名称
            result = re.sub(r"[^\w]", "", result)

            if result == "random" or result not in available_emotions:
                # LLM 无法确定或返回了无效的类别，随机选择
                logger.debug(f"{LOG_PREFIX} LLM 返回无效类别 '{result}'，随机选择")
                return random.choice(available_emotions)

            logger.info(f"{LOG_PREFIX} LLM 分析结果: {result}")
            return result

        except Exception as e:
            logger.error(f"{LOG_PREFIX} LLM 分析失败: {e}")
            # LLM 分析失败，回退到关键词分析
            return self._analyze_by_keywords(messages)

    def update_strategy(self, use_llm_analysis: bool) -> None:
        """更新分析策略。

        Args:
            use_llm_analysis: 是否使用 LLM 分析
        """
        self._use_llm_analysis = use_llm_analysis
        logger.info(
            f"{LOG_PREFIX} 分析策略已更新: {'LLM' if use_llm_analysis else '关键词'}"
        )

    def update_prompts(self, system_prompt: str = "", user_prompt: str = "") -> None:
        """更新 LLM 提示词。

        Args:
            system_prompt: 新的系统提示词，为空则使用默认提示词
            user_prompt: 新的用户提示词，为空则使用默认提示词
        """
        self._system_prompt = system_prompt
        self._user_prompt = user_prompt
        logger.debug(f"{LOG_PREFIX} LLM 提示词已更新")

    def update_category_mapping(self, category_mapping: dict[str, str]) -> None:
        """更新表情包类别映射。

        Args:
            category_mapping: 新的类别映射
        """
        self._category_mapping = category_mapping
        logger.debug(f"{LOG_PREFIX} 类别映射已更新，共 {len(category_mapping)} 个类别")
