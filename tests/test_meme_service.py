"""表情包服务单元测试。"""

import os
import tempfile

import pytest
from PIL import Image as PILImage

from ..services.meme_service import MemeService


class TestMemeService:
    """表情包服务测试类。"""

    def setup_method(self):
        """测试前准备。"""
        self.service = MemeService(convert_static_to_gif=False)

    def test_get_emotion_stats_empty(self):
        """测试获取统计 - 空目录。"""
        stats = self.service.get_emotion_stats()
        # 如果没有表情包目录，应该返回空或抛出异常
        # 这里根据实际实现调整
        assert isinstance(stats, dict)

    def test_convert_to_gif_disabled(self):
        """测试GIF转换 - 禁用。"""
        # 创建临时图片
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = PILImage.new("RGB", (100, 100), color="red")
            img.save(f, "PNG")
            temp_path = f.name

        try:
            # 禁用GIF转换，应返回原路径
            result = self.service.convert_to_gif(temp_path)
            assert result == temp_path
        finally:
            os.unlink(temp_path)

    def test_convert_to_gif_enabled(self):
        """测试GIF转换 - 启用。"""
        service = MemeService(convert_static_to_gif=True)

        # 创建临时图片
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img = PILImage.new("RGB", (100, 100), color="red")
            img.save(f, "PNG")
            temp_path = f.name

        try:
            # 启用GIF转换，应返回新路径
            result = service.convert_to_gif(temp_path)
            assert result != temp_path
            assert result.endswith(".gif")
            assert os.path.exists(result)

            # 清理生成的GIF
            os.unlink(result)
        finally:
            os.unlink(temp_path)

    def test_convert_to_gif_already_gif(self):
        """测试GIF转换 - 已经是GIF。"""
        service = MemeService(convert_static_to_gif=True)

        # 创建临时GIF
        with tempfile.NamedTemporaryFile(suffix=".gif", delete=False) as f:
            img = PILImage.new("RGB", (100, 100), color="red")
            img.save(f, "GIF")
            temp_path = f.name

        try:
            # 已经是GIF，应返回原路径
            result = service.convert_to_gif(temp_path)
            assert result == temp_path
        finally:
            os.unlink(temp_path)

    def test_get_available_emotions(self):
        """测试获取可用类别。"""
        emotions = self.service.get_available_emotions()
        assert isinstance(emotions, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
