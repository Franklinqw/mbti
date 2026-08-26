"""应用配置模块

集中管理 Flask 应用的各项配置参数,便于不同环境切换。
"""
from typing import Any


class Config:
    """应用基础配置类"""

    # 基础配置
    SECRET_KEY: str = "mbti-animal-test-secret-key-2026"

    # JSON 响应相关配置
    JSON_AS_ASCII: bool = False  # 支持中文直接输出,不转义为 ASCII

    # 静态文件与模板目录
    STATIC_FOLDER: str = "static"
    TEMPLATE_FOLDER: str = "templates"

    # 测试相关配置
    TOTAL_QUESTIONS: int = 20  # 测试题目总数(与需求文档一致)


class DevelopmentConfig(Config):
    """开发环境配置"""

    DEBUG: bool = True


class ProductionConfig(Config):
    """生产环境配置"""

    DEBUG: bool = False


# 环境配置映射表
CONFIG_MAP: dict[str, type[Config]] = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config(env: str = "default") -> Config:
    """根据环境名称获取配置实例

    Args:
        env: 环境名称,可选 development / production / default

    Returns:
        对应环境的配置实例
    """
    config_class = CONFIG_MAP.get(env, CONFIG_MAP["default"])
    return config_class()
