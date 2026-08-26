"""统一 API 响应工具

提供标准化的 RESTful API 响应格式,统一成功与错误的返回结构。
"""
from typing import Any

# 响应状态码常量
CODE_SUCCESS: int = 0       # 成功
CODE_ERROR: int = 1         # 通用错误
CODE_PARAM_ERROR: int = 2   # 参数错误


def success(data: Any = None, message: str = "操作成功") -> dict:
    """构造成功响应

    Args:
        data: 业务数据
        message: 提示信息

    Returns:
        标准化成功响应字典
    """
    return {
        "code": CODE_SUCCESS,
        "message": message,
        "data": data,
    }


def error(message: str = "操作失败", code: int = CODE_ERROR, data: Any = None) -> dict:
    """构造错误响应

    Args:
        message: 错误提示
        code: 错误码
        data: 附加数据

    Returns:
        标准化错误响应字典
    """
    return {
        "code": code,
        "message": message,
        "data": data,
    }
