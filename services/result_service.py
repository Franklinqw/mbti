"""结果服务

根据测试类型计算结果并构造报告:

  - simple / full:四字母 MBTI 类型匹配 16 种动物形象
  - pdp:五种动物气质取最高者
  - mental_age:分值映射心理年龄并落入气质分段
"""
from models.results import PersonalityResult, RESULT_MAP
from models.pdp_questions import PDP_RESULTS
from models.mental_age_questions import band_for_age
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
            mode: 测试模式

        Returns:
            包含类型、动物、性格描述与维度占比的结果字典

        Raises:
            ValueError: 结果类型不在题库定义之内时抛出
        """
        if mode in ('communication', 'big_five'):
            from services.rating_report_service import build_rating_report
            return build_rating_report(self._scoring_service.get_rating_scores(answers, mode), mode)
        mental_age = None
        if mode == 'pdp':
            # 1. 五种动物气质取最高
            side: str = self._scoring_service.calculate_pdp_type(answers, mode)
            result: PersonalityResult | None = PDP_RESULTS.get(side)
            if result is None:
                raise ValueError(f"未知的动物气质: {side}")
            dimensions: dict = self._scoring_service.get_pdp_scores(answers, mode)
            dimension_kind = 'single'
        elif mode == 'mental_age':
            mental_age = self._scoring_service.calculate_mental_age(answers, mode)
            result = band_for_age(mental_age)
            dimensions = self._scoring_service.get_mental_age_clusters(answers, mode)
            dimension_kind = 'single'
        else:
            # 2. 计算 MBTI 类型并匹配动物与性格结果
            mbti_type: str = self._scoring_service.calculate_mbti_type(answers, mode)
            result = self.get_result_by_type(mbti_type)
            if result is None:
                raise ValueError(f"未知的 MBTI 类型: {mbti_type}")
            dimensions = self._scoring_service.get_dimension_scores(answers, mode)
            dimension_kind = 'pair'

        report = {
            "mbtiType": f"{mental_age}岁" if mental_age is not None else result.mbti_type,
            "animal": result.animal,
            "emoji": result.emoji,
            "nickname": result.nickname,
            "traits": result.traits,
            "strengths": list(result.strengths),
            "weaknesses": list(result.weaknesses),
            "careers": list(result.careers),
            "dimensionKind": dimension_kind,
            "dimensions": dimensions,
        }
        if mental_age is not None:
            report["mentalAge"] = mental_age
        return report


# 模块级单例,供控制器层引用
result_service: ResultService = ResultService()
