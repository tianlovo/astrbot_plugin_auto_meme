"""群组上下文服务单元测试。"""

import pytest

from ..services.group_context_service import GroupContextService


class TestGroupContextService:
    """群组上下文服务测试类。"""

    def setup_method(self):
        """测试前准备。"""
        self.service = GroupContextService(
            window_size=5,
            enabled_groups=["123456", "789012"],
        )

    def test_add_message(self):
        """测试添加消息。"""
        count = self.service.add_message("123456", "测试消息")
        assert count == 1

        count = self.service.add_message("123456", "第二条消息")
        assert count == 2

    def test_should_trigger(self):
        """测试触发判断。"""
        # 添加3条消息，间隔为5，不应触发
        for i in range(3):
            self.service.add_message("123456", f"消息{i}")

        assert not self.service.should_trigger("123456", 5)

        # 再添加2条，达到5条，应触发
        for i in range(2):
            self.service.add_message("123456", f"消息{i+3}")

        assert self.service.should_trigger("123456", 5)

    def test_reset_counter(self):
        """测试重置计数器。"""
        for i in range(5):
            self.service.add_message("123456", f"消息{i}")

        assert self.service.should_trigger("123456", 5)

        self.service.reset_counter("123456")
        assert not self.service.should_trigger("123456", 5)

    def test_get_context(self):
        """测试获取上下文。"""
        for i in range(3):
            self.service.add_message("123456", f"消息{i}")

        context = self.service.get_context("123456")
        assert len(context) == 3
        assert context[0] == "消息0"
        assert context[2] == "消息2"

    def test_window_size_limit(self):
        """测试窗口大小限制。"""
        # 添加超过窗口大小的消息
        for i in range(10):
            self.service.add_message("123456", f"消息{i}")

        context = self.service.get_context("123456")
        # 窗口大小为5，只保留最新的5条
        assert len(context) == 5
        assert context[0] == "消息5"
        assert context[4] == "消息9"

    def test_is_group_enabled(self):
        """测试群白名单检查。"""
        assert self.service.is_group_enabled("123456")
        assert self.service.is_group_enabled("789012")
        assert not self.service.is_group_enabled("999999")

    def test_is_group_enabled_empty_list(self):
        """测试空白名单（允许所有群）。"""
        service = GroupContextService(
            window_size=5,
            enabled_groups=[],
        )
        assert service.is_group_enabled("123456")
        assert service.is_group_enabled("any_group")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
