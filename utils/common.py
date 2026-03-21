"""通用工具函数模块。

提供文件操作、JSON处理等通用工具函数。
"""

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def ensure_dir_exists(path: str) -> None:
    """确保目录存在，不存在则创建。

    Args:
        path: 目录路径
    """
    if not os.path.exists(path):
        os.makedirs(path)


def save_json(data: dict[str, Any], filepath: str) -> bool:
    """保存 JSON 数据到文件。

    Args:
        data: 要保存的数据
        filepath: 文件路径

    Returns:
        是否保存成功
    """
    try:
        ensure_dir_exists(os.path.dirname(filepath))
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"保存 JSON 文件失败 {filepath}: {e}")
        return False


def load_json(filepath: str, default: dict = None) -> dict:
    """从文件加载 JSON 数据。

    Args:
        filepath: 文件路径
        default: 默认返回值

    Returns:
        加载的数据或默认值
    """
    try:
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载 JSON 文件失败 {filepath}: {e}")
        return default if default is not None else {}
