"""语境分析器单元测试。"""

import pytest

from ..constants import EMOTION_KEYWORDS
from ..core.context_analyzer import ContextAnalyzer
from ..services.llm_service import LLMService
from ..models import LLMConfig


class TestContextAnalyzer:
    """语境分析器测试类。"""

    def setup_method(self):
        """测试前准备。"""
        category_mapping = {
            "happy": "开心",
            "angry": "生气",
            "sad": "难过",
        }
        llm_config = LLMConfig(
            use_llm_analysis=False,
            system_prompt="",
            user_prompt="",
        )
        self.llm_service = LLMService(
            context=None,
            config=llm_config,
            category_mapping=category_mapping,
        )
        self.analyzer = ContextAnalyzer(
            category_mapping=category_mapping,
            llm_service=self.llm_service,
        )

    def test_analyze_by_keywords_with_match(self):
        """测试关键词分析 - 有匹配。"""
        messages = ["今天真的好开心啊", "哈哈哈哈哈"]
        result = self.analyzer._analyze_by_keywords(messages)
        assert result == "happy"

    def test_analyze_by_keywords_with_angry(self):
        """测试关键词分析 - 生气。"""
        messages = ["气死我了", "真的很生气"]
        result = self.analyzer._analyze_by_keywords(messages)
        assert result == "angry"

    def test_analyze_by_keywords_no_match(self):
        """测试关键词分析 - 无匹配。"""
        messages = ["今天天气不错", "普通的一天"]
        result = self.analyzer._analyze_by_keywords(messages)
        # 无匹配时随机选择
        assert result in ["happy", "angry", "sad"]

    def test_analyze_by_keywords_empty(self):
        """测试关键词分析 - 空消息。"""
        messages = []
        result = self.analyzer._analyze_by_keywords(messages)
        assert result in ["happy", "angry", "sad"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
