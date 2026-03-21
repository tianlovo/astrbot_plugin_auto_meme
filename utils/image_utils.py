"""图片处理工具模块。

提供图片下载、格式检测和保存相关的工具函数。
"""

import io
import ssl
from pathlib import Path

import aiohttp
from PIL import Image as PILImage

from astrbot.api import logger

from ..constants import LOG_PREFIX, SUPPORTED_IMAGE_FORMATS


class ImageUtils:
    """图片处理工具类。

    提供图片下载、格式检测和保存的静态方法。
    支持 SSL 验证配置和异常处理。
    """

    # 图片格式到扩展名的映射
    FORMAT_EXTENSION_MAP = {
        "jpeg": ".jpg",
        "jpg": ".jpg",
        "png": ".png",
        "gif": ".gif",
        "webp": ".webp",
        "bmp": ".bmp",
        "tiff": ".tiff",
    }

    @staticmethod
    def _create_ssl_context(verify_ssl: bool = False) -> ssl.SSLContext:
        """创建 SSL 上下文。

        Args:
            verify_ssl: 是否验证 SSL 证书，默认为 False。

        Returns:
            配置好的 SSL 上下文对象。
        """
        ssl_context = ssl.create_default_context()
        if not verify_ssl:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        return ssl_context

    @staticmethod
    async def download_image(
        url: str, verify_ssl: bool = False, timeout: int = 30
    ) -> bytes:
        """下载图片并返回字节数据。

        使用 aiohttp 异步下载图片，支持 SSL 验证配置。

        Args:
            url: 图片的 URL 地址。
            verify_ssl: 是否验证 SSL 证书，默认为 False。
            timeout: 下载超时时间（秒），默认为 30 秒。

        Returns:
            图片的二进制字节数据。

        Raises:
            ValueError: 当 URL 为空或无效时。
            aiohttp.ClientError: 当下载过程中发生网络错误时。
            TimeoutError: 当下载超时时。

        Example:
            >>> content = await ImageUtils.download_image("https://example.com/image.png")
            >>> print(len(content))
            1024
        """
        if not url:
            raise ValueError("URL cannot be empty")

        ssl_context = ImageUtils._create_ssl_context(verify_ssl)

        try:
            async with aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=ssl_context),
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        raise aiohttp.ClientError(
                            f"Failed to download image, HTTP status: {resp.status}"
                        )
                    content = await resp.read()
                    logger.debug(
                        f"{LOG_PREFIX} Downloaded image from {url}, size: {len(content)} bytes"
                    )
                    return content
        except aiohttp.ClientError as e:
            logger.error(f"{LOG_PREFIX} Failed to download image from {url}: {e}")
            raise
        except Exception as e:
            logger.error(f"{LOG_PREFIX} Unexpected error downloading image: {e}")
            raise

    @staticmethod
    def detect_format(content: bytes) -> str:
        """检测图片格式。

        使用 PIL 库检测图片的二进制数据格式。

        Args:
            content: 图片的二进制字节数据。

        Returns:
            图片格式的小写字符串（如 'jpeg', 'png', 'gif' 等）。
            如果无法检测，返回 'unknown'。

        Example:
            >>> format_type = ImageUtils.detect_format(image_bytes)
            >>> print(format_type)
            'png'
        """
        if not content:
            return "unknown"

        try:
            with PILImage.open(io.BytesIO(content)) as img:
                file_type = img.format.lower() if img.format else "unknown"
                logger.debug(f"{LOG_PREFIX} Detected image format: {file_type}")
                return file_type
        except Exception as e:
            logger.warning(f"{LOG_PREFIX} Failed to detect image format: {e}")
            return "unknown"

    @staticmethod
    def get_extension(image_format: str) -> str:
        """根据图片格式获取文件扩展名。

        Args:
            image_format: 图片格式（如 'jpeg', 'png' 等）。

        Returns:
            对应的文件扩展名（如 '.jpg', '.png' 等）。
            如果格式未知，返回 '.bin'。
        """
        if not image_format:
            return ".bin"

        normalized_format = image_format.lower()
        return ImageUtils.FORMAT_EXTENSION_MAP.get(normalized_format, ".bin")

    @staticmethod
    def save_image(content: bytes, save_path: Path | str) -> Path:
        """保存图片到指定路径。

        自动创建目标目录（如果不存在）。

        Args:
            content: 图片的二进制字节数据。
            save_path: 保存路径，可以是字符串或 Path 对象。

        Returns:
            保存后的文件 Path 对象。

        Raises:
            ValueError: 当内容为空时。
            IOError: 当文件写入失败时。

        Example:
            >>> path = ImageUtils.save_image(image_bytes, "/path/to/image.png")
            >>> print(path.exists())
            True
        """
        if not content:
            raise ValueError("Content cannot be empty")

        save_path = Path(save_path)

        try:
            # 创建父目录（如果不存在）
            save_path.parent.mkdir(parents=True, exist_ok=True)

            with open(save_path, "wb") as f:
                f.write(content)

            logger.debug(
                f"{LOG_PREFIX} Saved image to {save_path}, size: {len(content)} bytes"
            )
            return save_path
        except OSError as e:
            logger.error(f"{LOG_PREFIX} Failed to save image to {save_path}: {e}")
            raise
        except Exception as e:
            logger.error(f"{LOG_PREFIX} Unexpected error saving image: {e}")
            raise

    @staticmethod
    def is_supported_format(image_format: str) -> bool:
        """检查图片格式是否受支持。

        Args:
            image_format: 图片格式（如 'jpeg', 'png' 等）。

        Returns:
            如果格式在 SUPPORTED_IMAGE_FORMATS 中则返回 True，否则返回 False。
        """
        if not image_format:
            return False

        ext = ImageUtils.get_extension(image_format)
        return ext.lower() in (fmt.lower() for fmt in SUPPORTED_IMAGE_FORMATS)

    @staticmethod
    async def download_and_save(
        url: str,
        save_dir: Path | str,
        filename: str | None = None,
        verify_ssl: bool = False,
    ) -> Path:
        """下载图片并保存到指定目录。

        如果未提供文件名，将自动生成带正确扩展名的文件名。

        Args:
            url: 图片的 URL 地址。
            save_dir: 保存目录路径。
            filename: 可选的文件名（不含扩展名），默认为 None。
            verify_ssl: 是否验证 SSL 证书，默认为 False。

        Returns:
            保存后的文件完整路径。

        Raises:
            ValueError: 当 URL 为空时。
            aiohttp.ClientError: 当下载失败时。
            IOError: 当保存失败时。
        """
        if not url:
            raise ValueError("URL cannot be empty")

        # 下载图片
        content = await ImageUtils.download_image(url, verify_ssl)

        # 检测格式
        image_format = ImageUtils.detect_format(content)
        extension = ImageUtils.get_extension(image_format)

        # 构建保存路径
        save_dir = Path(save_dir)
        if filename:
            save_path = save_dir / f"{filename}{extension}"
        else:
            import time

            timestamp = int(time.time())
            save_path = save_dir / f"{timestamp}{extension}"

        # 保存图片
        return ImageUtils.save_image(content, save_path)
