"""MBTI 测试控制器

提供测试相关的 RESTful API 接口:
  - GET  /api/questions  获取全部测试题目
  - POST /api/result     提交答案并获取 MBTI 结果
"""
from typing import Any
from uuid import uuid4

from flask import Blueprint, request, jsonify
from sqlalchemy import select
from models.database import TestAttempt, TestResult, get_db
from services.auth_service import current_user, login_required

from services.question_service import question_service, SUPPORTED_MODES
from services.result_service import result_service
from utils.response import success, error, CODE_PARAM_ERROR

# 创建蓝图
mbti_bp: Blueprint = Blueprint("mbti", __name__, url_prefix="/api")


@mbti_bp.route("/questions", methods=["GET"])
@login_required
def get_questions() -> Any:
    """获取全部测试题目

    返回所有题目的序号、题干与选项,供前端逐题展示。
    """
    mode = request.args.get("mode", "simple")
    if not isinstance(mode, str) or mode not in SUPPORTED_MODES:
        return jsonify(error(message="无效的测试模式", code=CODE_PARAM_ERROR)), 400
    questions: list[dict] = question_service.get_question_dicts(mode)
    total: int = question_service.get_total_count(mode)
    return jsonify(success(data={
        "total": total,
        "questions": questions,
    }, message="题目获取成功"))


def attempt_payload(attempt):
    return {'attemptId': attempt.id, 'mode': attempt.mode,
            'questions': question_service.get_question_dicts(attempt.mode),
            'total': question_service.get_total_count(attempt.mode)}


@mbti_bp.post('/attempts')
@login_required
def create_attempt():
    data = request.get_json(silent=True)
    mode = data.get('mode') if isinstance(data, dict) else None
    if not isinstance(mode, str) or mode not in SUPPORTED_MODES:
        return jsonify(error('无效的测试模式')), 400
    attempt = TestAttempt(id=str(uuid4()), user_id=current_user().id, mode=mode)
    db = get_db()
    db.add(attempt)
    db.commit()
    return jsonify(success(attempt_payload(attempt))), 201


@mbti_bp.get('/attempts/<attempt_id>')
@login_required
def get_attempt(attempt_id):
    attempt = get_db().scalar(select(TestAttempt).where(
        TestAttempt.id == attempt_id, TestAttempt.user_id == current_user().id))
    if not attempt:
        return jsonify(error('测试记录不存在，请重新开始')), 404
    return jsonify(success(attempt_payload(attempt)))


def saved_result(record):
    return {**record.report, 'recordId': record.id,
            'startedAt': record.summary()['startedAt'],
            'completedAt': record.summary()['completedAt']}


@mbti_bp.route("/result", methods=["POST"])
@login_required
def submit_result() -> Any:
    """提交答案并获取 MBTI 结果

    请求体 JSON:
        {"answers": [{"questionIndex": 1, "optionKey": "A"}, ...]}

    校验答案完整性后,计算 MBTI 类型并返回对应的动物与性格描述。
    """
    data: dict = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify(error(message="请求体必须为对象", code=CODE_PARAM_ERROR)), 400
    mode = data.get("mode", "simple")
    if not isinstance(mode, str) or mode not in SUPPORTED_MODES:
        return jsonify(error(message="无效的测试模式", code=CODE_PARAM_ERROR)), 400
    answers: list[dict] = data.get("answers")

    # 参数校验:answers 必须为非空列表
    if not isinstance(answers, list) or not answers:
        return jsonify(error(message="答案列表不能为空",
                             code=CODE_PARAM_ERROR)), 400

    total: int = question_service.get_total_count(mode)
    if len(answers) != total:
        return jsonify(error(
            message=f"答案数量不完整,需 {total} 题,实际 {len(answers)} 题",
            code=CODE_PARAM_ERROR)), 400

    try:
        db = get_db()
        attempt_id = data.get('attemptId')
        if not isinstance(attempt_id, str) or len(attempt_id) > 36:
            return jsonify(error('请先开始一次测试')), 400
        attempt = db.scalar(select(TestAttempt).where(
            TestAttempt.id == attempt_id, TestAttempt.user_id == current_user().id
        ).with_for_update())
        if not attempt or attempt.mode != mode:
            return jsonify(error('测试记录与账号或模式不匹配')), 400
        previous = db.scalar(select(TestResult).where(
            TestResult.user_id == current_user().id, TestResult.attempt_id == attempt_id))
        if previous:
            return jsonify(success(saved_result(previous), '结果已保存'))
        result_detail: dict = result_service.build_result_detail(answers, mode)
        record = TestResult(user_id=current_user().id, attempt_id=attempt.id,
                            mode=mode, mbti_type=result_detail['mbtiType'],
                            answers=answers, report=result_detail, started_at=attempt.started_at)
        db.add(record)
        db.commit()
        return jsonify(success(data=saved_result(record), message="测试结果已保存到个人中心"))
    except ValueError as e:
        # 答案非法等业务异常
        return jsonify(error(message=str(e), code=CODE_PARAM_ERROR)), 400
