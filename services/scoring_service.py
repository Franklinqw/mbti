"""计分服务

根据用户作答记录统计结果,按测试类型分为三种计分方式:

  - 对立二选一(simple / full):统计 MBTI 四个维度两端票数,
    每个维度取较高一端拼成四字母类型
  - 多桶取最高(pdp):统计五种动物气质各被选中的次数,取最高者
  - 分值累加(mental_age):累加各选项的成熟度分值,
    线性映射到 12–60 岁的心理年龄并落入分段
"""
from typing import Any, Iterator

from models.questions import DIMENSION_LETTERS, Option, Question
from models.pdp_questions import PDP_NAMES, PDP_SIDES
from models.mental_age_questions import (AGE_MAX, AGE_MIN, CLUSTER_LABELS,
                                         MENTAL_AGE_SCORE_MAX, MENTAL_AGE_SCORE_MIN)
from services.question_service import question_service


class ScoringService:
    """计分服务类"""

    def get_rating_scores(self, answers, mode):
        from models.big_five_questions import BIG_FIVE_NAMES
        from models.communication_questions import COMMUNICATION_NAMES
        names = BIG_FIVE_NAMES if mode == 'big_five' else COMMUNICATION_NAMES
        totals = {key: 0 for key in names}
        counts = {key: 0 for key in names}
        for question, option in self._validated_pairs(answers, mode):
            totals[question.dimension] += option.score
            counts[question.dimension] += 1
        return {key: {'label': label, 'score': totals[key], 'count': counts[key],
                      'mean': round(totals[key] / counts[key], 2),
                      'percent': round((totals[key] - counts[key]) / (4 * counts[key]) * 100)}
                for key, label in names.items()}

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

    def _validated_pairs(self, answers: list[dict[str, Any]],
                         mode: str) -> Iterator[tuple[Question, Option]]:
        """公共答案校验,逐条产出 (题目, 选中选项)

        Args:
            answers: 作答列表,每项为 {"questionIndex": int, "optionKey": str}
            mode: 测试模式

        Raises:
            ValueError: 数量不符、题号重复或选项非法时抛出
        """
        total: int = self._question_service.get_total_count(mode)
        if len(answers) != total:
            raise ValueError(
                f"答案数量不完整,需 {total} 题,实际 {len(answers)} 题")
        seen: set[int] = set()
        for ans in answers:
            if not isinstance(ans, dict):
                raise ValueError("每条答案必须为对象")
            index = ans.get("questionIndex")
            if type(index) is not int or index in seen:
                raise ValueError("题号必须为不重复的整数")
            seen.add(index)
            opt_key: str = ans.get("optionKey")
            if not self._question_service.validate_answer(index, opt_key, mode):
                raise ValueError(f"非法答案:第{index}题选项{opt_key}")
            question = self._question_service.get_question_by_index(index, mode)
            for opt in question.options:
                if opt.key == opt_key:
                    yield question, opt
                    break

    def calculate_mbti_type(self, answers: list[dict[str, Any]], mode: str = "simple") -> str:
        """根据作答列表计算 MBTI 类型

        Args:
            answers: 作答列表,每项为 {"questionIndex": int, "optionKey": str}

        Returns:
            四字母 MBTI 类型,如 "INTJ"

        Raises:
            ValueError: 答案数量不足或存在非法答案时抛出
        """
        # 1. 校验并统计每个维度的得分
        scores: dict[str, dict[str, int]] = self._init_scores()
        for _, opt in self._validated_pairs(answers, mode):
            scores[opt.dimension][opt.side] += 1

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
            mode: 测试模式

        Returns:
            各维度两端得分与占比
        """
        scores: dict[str, dict[str, int]] = self._init_scores()
        for _, opt in self._validated_pairs(answers, mode):
            scores[opt.dimension][opt.side] += 1

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

    def calculate_pdp_type(self, answers: list[dict[str, Any]], mode: str = "pdp") -> str:
        """统计五种动物气质票数,返回最高者的代号

        Args:
            answers: 作答列表

        Returns:
            动物代号,如 "TIGER";平局时按 PDP_SIDES 顺序取先出现者,
            保证同一组答案结果稳定

        Raises:
            ValueError: 答案数量不足或存在非法答案时抛出
        """
        votes: dict[str, int] = {side: 0 for side in PDP_SIDES}
        for _, opt in self._validated_pairs(answers, mode):
            votes[opt.side] += 1
        best = PDP_SIDES[0]
        for side in PDP_SIDES[1:]:
            if votes[side] > votes[best]:
                best = side
        return best

    def get_pdp_scores(self, answers: list[dict[str, Any]], mode: str = "pdp") -> dict:
        """获取五种动物气质的票数与占比(供结果页展示)

        Args:
            answers: 作答列表

        Returns:
            各动物的票数与占全部作答的百分比
        """
        votes: dict[str, int] = {side: 0 for side in PDP_SIDES}
        total = 0
        for _, opt in self._validated_pairs(answers, mode):
            votes[opt.side] += 1
            total += 1
        return {side: {"label": PDP_NAMES[side], "score": votes[side],
                       "percent": round(votes[side] / total * 100) if total else 0}
                for side in PDP_SIDES}

    def calculate_mental_age(self, answers: list[dict[str, Any]], mode: str = "mental_age") -> int:
        """累加选项成熟度分值,线性映射到心理年龄

        Args:
            answers: 作答列表

        Returns:
            12–60 之间的心理年龄(岁)

        Raises:
            ValueError: 答案数量不足或存在非法答案时抛出
        """
        total = sum(opt.score for _, opt in self._validated_pairs(answers, mode))
        span = MENTAL_AGE_SCORE_MAX - MENTAL_AGE_SCORE_MIN
        age = AGE_MIN + round((total - MENTAL_AGE_SCORE_MIN) * (AGE_MAX - AGE_MIN) / span)
        return max(AGE_MIN, min(AGE_MAX, age))

    def get_mental_age_clusters(self, answers: list[dict[str, Any]],
                                mode: str = "mental_age") -> dict:
        """获取作答风格集群的分布(供结果页展示)

        Args:
            answers: 作答列表

        Returns:
            各集群被选次数与占全部作答的百分比
        """
        counts: dict[str, int] = {cluster: 0 for cluster in CLUSTER_LABELS}
        total = 0
        for _, opt in self._validated_pairs(answers, mode):
            counts[opt.side] += 1
            total += 1
        return {cluster: {"label": CLUSTER_LABELS[cluster], "score": counts[cluster],
                          "percent": round(counts[cluster] / total * 100) if total else 0}
                for cluster in CLUSTER_LABELS}


# 模块级单例,供控制器层引用
scoring_service: ScoringService = ScoringService()
