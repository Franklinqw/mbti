"""MBTI 测试控制器

提供测试相关的 RESTful API 接口:
  - GET  /api/questions  获取全部测试题目
  - POST /api/result     提交答案并获取 MBTI 结果
"""
from typing import Any

from flask import Blueprint, request, jsonify

from services.question_service import question_service
from services.result_service import result_service
from utils.response import success, error, CODE_PARAM_ERROR

# 创建蓝图
mbti_bp: Blueprint = Blueprint("mbti", __name__, url_prefix="/api")


@mbti_bp.route("/questions", methods=["GET"])
def get_questions() -> Any:
    """获取全部测试题目

    返回所有题目的序号、题干与选项,供前端逐题展示。
    """
    questions: list[dict] = question_service.get_question_dicts()
    total: int = question_service.get_total_count()
    return jsonify(success(data={
        "total": total,
        "questions": questions,
    }, message="题目获取成功"))


@mbti_bp.route("/result", methods=["POST"])
def submit_result() -> Any:
    """提交答案并获取 MBTI 结果

    请求体 JSON:
        {"answers": [{"questionIndex": 1, "optionKey": "A"}, ...]}

    校验答案完整性后,计算 MBTI 类型并返回对应的动物与性格描述。
    """
    data: dict = request.get_json(silent=True) or {}
    answers: list[dict] = data.get("answers")

    # 参数校验:answers 必须为非空列表
    if not isinstance(answers, list) or not answers:
        return jsonify(error(message="答案列表不能为空",
                             code=CODE_PARAM_ERROR)), 400

    total: int = question_service.get_total_count()
    if len(answers) != total:
        return jsonify(error(
            message=f"答案数量不完整,需 {total} 题,实际 {len(answers)} 题",
            code=CODE_PARAM_ERROR)), 400

    try:
        result_detail: dict = result_service.build_result_detail(answers)
        return jsonify(success(data=result_detail, message="测试结果生成成功"))
    except ValueError as e:
        # 答案非法等业务异常
        return jsonify(error(message=str(e), code=CODE_PARAM_ERROR)), 400
