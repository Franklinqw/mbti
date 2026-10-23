"""结果服务

根据 MBTI 类型匹配对应的动物形象与性格描述结果。
"""
from models.results import PersonalityResult, RESULT_MAP
from services.scoring_service import scoring_service


class ResultService:
    """结果服务类"""

    def __init__(self) -> None:
        """初始化结果服务"""
        self._scoring_service = scoring_service

    def get_result_by_type(self, mbti_type: str) -> PersonalityResult | None:
        """根据 MBTI 类型获取结果

        Args:
            mbti_type: 四字母 MBTI 类型,如 "INTJ"

        Returns:
            人格结果对象,类型不存在时返回 None
        """
        return RESULT_MAP.get(mbti_type.upper())

    def build_result_detail(self, answers: list[dict], mode: str = "simple") -> dict:
        """根据完整作答计算并构造结果详情

        Args:
            answers: 作答列表

        Returns:
            包含 MBTI 类型、动物、性格描述、维度占比的结果字典

        Raises:
            ValueError: MBTI 类型不在 16 种之内时抛出
        """
        # 1. 计算 MBTI 类型
        mbti_type: str = self._scoring_service.calculate_mbti_type(answers, mode)

        # 2. 匹配动物与性格结果
        result: PersonalityResult | None = self.get_result_by_type(mbti_type)
        if result is None:
            raise ValueError(f"未知的 MBTI 类型: {mbti_type}")

        # 3. 获取各维度占比,供前端展示倾向强度
        dimension_detail: dict = \
            self._scoring_service.get_dimension_scores(answers, mode)

        return {
            "mbtiType": result.mbti_type,
            "animal": result.animal,
            "emoji": result.emoji,
            "nickname": result.nickname,
            "traits": result.traits,
            "strengths": list(result.strengths),
            "weaknesses": list(result.weaknesses),
            "careers": list(result.careers),
            "dimensions": dimension_detail,
        }


# 模块级单例,供控制器层引用
result_service: ResultService = ResultService()
