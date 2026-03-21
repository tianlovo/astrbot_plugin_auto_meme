"""通用工具函数模块。

提供文件操作、JSON处理等通用工具函数。
"""

import json
import logging
import os
import shutil
from typing import Any

from ..config import CURRENT_DIR, MEMES_DIR

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


def copy_memes_if_not_exists():
    """如果 MEMES_DIR 下没有表情包文件，则复制 CURRENT_DIR 下的 memes 文件夹内容。"""
    # 确保目录存在
    ensure_dir_exists(MEMES_DIR)

    # 检查目录是否为空或只有非常少的文件（可能是残留或系统生成文件）
    meme_files = [
        f for f in os.listdir(MEMES_DIR) if os.path.isfile(os.path.join(MEMES_DIR, f))
    ]

    # 如果目录为空或几乎为空，复制默认表情包
    if len(meme_files) < 3:  # 假设少于3个文件认为是空目录
        source_dir = os.path.join(CURRENT_DIR, "memes")
        if os.path.exists(source_dir):
            # 复制所有文件
            for item in os.listdir(source_dir):
                src_path = os.path.join(source_dir, item)
                dst_path = os.path.join(MEMES_DIR, item)
                if os.path.isdir(src_path):
                    if not os.path.exists(dst_path):
                        shutil.copytree(src_path, dst_path)
                else:
                    shutil.copy2(src_path, dst_path)
            logger.info(f"已将默认表情包复制到 {MEMES_DIR}")
        else:
            logger.warning(f"默认表情包目录不存在: {source_dir}")
