"""计分服务

根据用户作答记录,统计 MBTI 四个维度的得分,并确定最终人格类型。

计分规则(符合需求文档 4.1):
  - 每道题目的选项对应 MBTI 四个维度的不同倾向
  - 用户选择选项后,系统记录对应维度的得分
  - 完成所有题目后,系统统计四个维度的得分
  - 根据每个维度的得分高低确定用户的 MBTI 类型
    (例如:E>I、N>S、T>F、J>P,则结果为 ENTJ)
"""
from typing import Any

from models.questions import DIMENSION_LETTERS, Question
from services.question_service import question_service


class ScoringService:
    """计分服务类"""

    def __init__(self) -> None:
        """初始化计分服务"""
        self._question_service = question_service

    def _init_scores(self) -> dict[str, dict[str, int]]:
        """初始化四个维度的得分统计结构

        Returns:
            各维度两端字母的得分字典,例如 {"EI": {"E": 0, "I": 0}}
        """
        scores: dict[str, dict[str, int]] = {}
        for dim, (left, right) in DIMENSION_LETTERS.items():
            scores[dim] = {left: 0, right: 0}
        return scores

    def calculate_mbti_type(self, answers: list[dict[str, Any]], mode: str = "simple") -> str:
        """根据作答列表计算 MBTI 类型

        Args:
            answers: 作答列表,每项为 {"questionIndex": int, "optionKey": str}

        Returns:
            四字母 MBTI 类型,如 "INTJ"

        Raises:
            ValueError: 答案数量不足或存在非法答案时抛出
        """
        total: int = self._question_service.get_total_count(mode)
        if len(answers) != total:
            raise ValueError(
                f"答案数量不完整,需 {total} 题,实际 {len(answers)} 题")

        # 1. 校验并统计每个维度的得分
        scores: dict[str, dict[str, int]] = self._init_scores()
        seen = set()
        for ans in answers:
            if not isinstance(ans, dict):
                raise ValueError("每条答案必须为对象")
            index = ans.get("questionIndex")
            if type(index) is not int or index in seen:
                raise ValueError("题号必须为不重复的整数")
            seen.add(index)
            q_index: int = ans.get("questionIndex")
            opt_key: str = ans.get("optionKey")
            if not self._question_service.validate_answer(q_index, opt_key, mode):
                raise ValueError(f"非法答案:第{q_index}题选项{opt_key}")

            question: Question | None = \
                self._question_service.get_question_by_index(q_index, mode)
            # 选取对应选项,累加该维度端点得分
            for opt in question.options:
                if opt.key == opt_key:
                    scores[opt.dimension][opt.side] += 1
                    break

        # 2. 逐维度比较得分高低,取较高的一端拼成 MBTI 类型
        mbti_chars: list[str] = []
        for dim in ("EI", "SN", "TF", "JP"):
            left, right = DIMENSION_LETTERS[dim]
            left_score: int = scores[dim][left]
            right_score: int = scores[dim][right]
            # 得分相等时默认取左端(E/S/T/J),保证结果稳定
            mbti_chars.append(left if left_score >= right_score else right)

        return "".join(mbti_chars)

    def get_dimension_scores(self, answers: list[dict[str, Any]], mode: str = "simple") -> dict:
        """获取各维度的详细得分(供结果页展示倾向比例)

        Args:
            answers: 作答列表

        Returns:
            各维度两端得分与占比
        """
        scores: dict[str, dict[str, int]] = self._init_scores()
        for ans in answers:
            q_index: int = ans.get("questionIndex")
            opt_key: str = ans.get("optionKey")
            question: Question | None = \
                self._question_service.get_question_by_index(q_index, mode)
            if question is None:
                continue
            for opt in question.options:
                if opt.key == opt_key:
                    scores[opt.dimension][opt.side] += 1
                    break

        # 计算各维度占比
        detail: dict = {}
        for dim in ("EI", "SN", "TF", "JP"):
            left, right = DIMENSION_LETTERS[dim]
            total_dim: int = scores[dim][left] + scores[dim][right]
            detail[dim] = {
                "left": {"letter": left, "score": scores[dim][left],
                          "percent": round(scores[dim][left] / total_dim * 100) if total_dim else 0},
                "right": {"letter": right, "score": scores[dim][right],
                           "percent": round(scores[dim][right] / total_dim * 100) if total_dim else 0},
            }
        return detail


# 模块级单例,供控制器层引用
scoring_service: ScoringService = ScoringService()
