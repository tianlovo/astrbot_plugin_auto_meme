"""语境分析器模块。

封装关键词分析和 LLM 分析两种策略，根据配置自动选择策略。
"""

import random
import re
from datetime import datetime
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
        _timezone: 时区设置
        _llm_provider_id: 指定的 LLM Provider ID
    """

    def __init__(
        self,
        astrbot_context: "Context",
        category_mapping: dict[str, str],
        use_llm_analysis: bool = True,
        system_prompt: str = "",
        user_prompt: str = "",
        timezone: str = "Asia/Shanghai",
        llm_provider_id: str = "",
        debug_prompt: bool = False,
    ):
        """初始化语境分析器。

        Args:
            astrbot_context: AstrBot 上下文对象，用于调用 LLM
            category_mapping: 表情包类别映射 {类别名: 描述}
            use_llm_analysis: 是否使用 LLM 分析，默认为 True
            system_prompt: 自定义系统提示词，为空则使用默认提示词
            user_prompt: 自定义用户提示词，为空则使用默认提示词
            timezone: 时区设置，默认为 Asia/Shanghai
            llm_provider_id: 指定的 LLM Provider ID，为空则使用当前会话的 Provider
            debug_prompt: 是否打印完整提示词到日志
        """
        self._astrbot_context = astrbot_context
        self._category_mapping = category_mapping
        self._use_llm_analysis = use_llm_analysis
        self._system_prompt = system_prompt
        self._user_prompt = user_prompt
        self._timezone = timezone
        self._llm_provider_id = llm_provider_id
        self._debug_prompt = debug_prompt

        provider_info = f"Provider: {llm_provider_id if llm_provider_id else '自动'}"
        logger.info(
            f"{LOG_PREFIX} 语境分析器已初始化，使用策略: {'LLM' if use_llm_analysis else '关键词'}, {provider_info}"
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
        logger.info(
            f"{LOG_PREFIX} 🔍 开始语境分析 | 策略: {'LLM' if self._use_llm_analysis else '关键词'} | "
            f"消息数: {len(messages)} | 可用类别: {len(self._category_mapping)}"
        )

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
            selected = random.choice(list(self._category_mapping.keys()))
            logger.info(f"{LOG_PREFIX} 📭 消息为空，随机选择: {selected}")
            return selected

        # 合并所有消息文本
        context_text = "\n".join(messages)
        logger.debug(f"{LOG_PREFIX} 📝 分析文本长度: {len(context_text)} 字符")

        # 统计每个类别的关键词匹配次数
        scores: dict[str, int] = {}
        for emotion, keywords in EMOTION_KEYWORDS.items():
            if emotion not in self._category_mapping:
                continue
            score = 0
            matched_keywords = []
            for keyword in keywords:
                count = len(re.findall(re.escape(keyword), context_text, re.IGNORECASE))
                if count > 0:
                    score += count
                    matched_keywords.append(f"{keyword}({count})")
            if score > 0:
                scores[emotion] = score
                logger.debug(f"{LOG_PREFIX} 🎯 类别 '{emotion}' 匹配: {matched_keywords} = {score}分")

        if not scores:
            # 没有匹配到关键词，随机选择
            selected = random.choice(list(self._category_mapping.keys()))
            logger.info(f"{LOG_PREFIX} 🎲 关键词分析未匹配，随机选择: {selected}")
            return selected

        # 选择得分最高的类别
        max_score = max(scores.values())
        best_emotions = [e for e, s in scores.items() if s == max_score]
        selected = random.choice(best_emotions)

        logger.info(
            f"{LOG_PREFIX} 🏆 关键词分析结果: {selected} | 得分: {max_score} | "
            f"候选: {best_emotions}"
        )
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
            selected = random.choice(list(self._category_mapping.keys()))
            logger.info(f"{LOG_PREFIX} 📭 消息为空，随机选择: {selected}")
            return selected

        # 合并所有消息文本
        context_text = "\n".join(messages)

        # 构建可用的表情包类别列表（包含描述）
        available_emotions = list(self._category_mapping.keys())
        emotions_list = "\n".join(
            [f"- {emotion}: {desc}" for emotion, desc in self._category_mapping.items()]
        )

        logger.debug(f"{LOG_PREFIX} 🤖 可用类别:\n{emotions_list}")

        # 获取当前时间（指定时区）
        try:
            from zoneinfo import ZoneInfo
            current_time = datetime.now(ZoneInfo(self._timezone)).strftime("%Y-%m-%d %H:%M")
        except Exception:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M")

        # 构建系统提示词
        if self._system_prompt:
            system_prompt = self._system_prompt.format(
                emotions_list=emotions_list,
                current_time=current_time
            )
            logger.debug(f"{LOG_PREFIX} 📝 使用自定义系统提示词")
        else:
            system_prompt = DEFAULT_SYSTEM_PROMPT.format(
                emotions_list=emotions_list,
                current_time=current_time
            )
            logger.debug(f"{LOG_PREFIX} 📝 使用默认系统提示词")

        # 构建用户提示词
        if self._user_prompt:
            user_prompt = self._user_prompt.format(context_text=context_text)
            logger.debug(f"{LOG_PREFIX} 📝 使用自定义用户提示词")
        else:
            user_prompt = DEFAULT_USER_PROMPT.format(context_text=context_text)
            logger.debug(f"{LOG_PREFIX} 📝 使用默认用户提示词")

        # 如果开启调试模式，打印完整提示词
        if self._debug_prompt:
            logger.info(f"{LOG_PREFIX} 🔍 [调试模式] 完整系统提示词:\n{'='*50}\n{system_prompt}\n{'='*50}")
            logger.info(f"{LOG_PREFIX} 🔍 [调试模式] 完整用户提示词:\n{'='*50}\n{user_prompt}\n{'='*50}")

        try:
            # 获取 Provider ID（优先使用配置的，否则使用当前会话的）
            provider_id = await self._get_provider_id(event)

            if not provider_id:
                logger.warning(f"{LOG_PREFIX} ⚠️ 无法获取 LLM provider ID，回退到关键词分析")
                return self._analyze_by_keywords(messages)

            logger.info(f"{LOG_PREFIX} 🤖 调用 LLM 分析 | Provider: {provider_id}")

            # 调用 LLM
            llm_resp = await self._astrbot_context.llm_generate(
                chat_provider_id=provider_id,
                prompt=user_prompt,
                system_prompt=system_prompt,
            )

            # 解析 LLM 响应
            raw_result = llm_resp.completion_text.strip()
            logger.debug(f"{LOG_PREFIX} 🤖 LLM 原始响应: {raw_result}")

            # 清理 <think> 标签及其内容（某些模型会输出思考过程）
            # 处理两种情况：1. 完整的 <think>...</think>  2. 只有 </think> 结束标签
            cleaned_result = re.sub(r"<think>.*?</think>", "", raw_result, flags=re.DOTALL)
            cleaned_result = re.sub(r"</think>", "", cleaned_result)

            # 尝试解析新的响应格式：类别: xxx\n原因: yyy
            emotion_match = re.search(r"类别[:：]\s*(\w+)", cleaned_result, re.IGNORECASE)
            reason_match = re.search(r"原因[:：]\s*(.+?)(?:\n|$)", cleaned_result, re.IGNORECASE | re.DOTALL)

            if emotion_match:
                result = emotion_match.group(1).lower().strip()
                reason = reason_match.group(1).strip() if reason_match else "未提供"
            else:
                # 回退到旧格式：提取最后一个有效单词作为类别名称
                # 按行分割，取最后一行，然后提取第一个单词
                lines = [line.strip() for line in cleaned_result.split('\n') if line.strip()]
                if lines:
                    last_line = lines[-1]
                    # 提取第一个单词（只保留字母）
                    word_match = re.search(r"[a-zA-Z]+", last_line)
                    if word_match:
                        result = word_match.group(0).lower()
                    else:
                        result = ""
                else:
                    result = ""
                reason = "未提供"

            logger.debug(f"{LOG_PREFIX} 🤖 LLM 解析结果: 类别={result}, 原因={reason}")

            if result == "random" or result not in available_emotions:
                # LLM 无法确定或返回了无效的类别，随机选择
                selected = random.choice(available_emotions)
                logger.warning(
                    f"{LOG_PREFIX} ⚠️ LLM 返回无效类别 '{raw_result}' -> '{result}'，"
                    f"随机选择: {selected}"
                )
                return selected

            logger.info(f"{LOG_PREFIX} ✅ LLM 分析成功: {result} | 原因: {reason}")
            return result

        except Exception as e:
            logger.error(f"{LOG_PREFIX} ❌ LLM 分析失败: {e}")
            logger.info(f"{LOG_PREFIX} 🔄 回退到关键词分析")
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

    async def _get_provider_id(self, event: AstrMessageEvent) -> str | None:
        """获取 LLM Provider ID。

        优先使用配置的 Provider ID，如果未配置或无效则使用当前会话的 Provider。

        Args:
            event: 消息事件对象

        Returns:
            Provider ID 或 None
        """
        # 如果配置了特定的 Provider ID，先尝试使用它
        if self._llm_provider_id:
            # 检查配置的 Provider 是否存在
            provider = self._astrbot_context.get_provider_by_id(self._llm_provider_id)
            if provider:
                logger.debug(f"{LOG_PREFIX} 使用配置的 Provider: {self._llm_provider_id}")
                return self._llm_provider_id
            else:
                logger.warning(
                    f"{LOG_PREFIX} 配置的 Provider '{self._llm_provider_id}' 不存在，"
                    f"将尝试使用当前会话的 Provider"
                )

        # 回退到当前会话的 Provider
        try:
            umo = event.unified_msg_origin
            provider_id = await self._astrbot_context.get_current_chat_provider_id(umo=umo)
            return provider_id
        except Exception as e:
            logger.warning(f"{LOG_PREFIX} 获取当前会话 Provider ID 失败: {e}")
            return None

    def update_category_mapping(self, category_mapping: dict[str, str]) -> None:
        """更新表情包类别映射。

        Args:
            category_mapping: 新的类别映射
        """
        self._category_mapping = category_mapping
        logger.debug(f"{LOG_PREFIX} 类别映射已更新，共 {len(category_mapping)} 个类别")
