"""题目服务

负责获取测试题目列表与题目数量等信息。
"""
from models.questions import QUESTIONS, Question
from models.extended_questions import FULL_QUESTIONS
from models.pdp_questions import PDP_QUESTIONS
from models.mental_age_questions import MENTAL_AGE_QUESTIONS
from models.big_five_questions import BIG_FIVE_QUESTIONS
from models.communication_questions import COMMUNICATION_QUESTIONS

# 支持的测试类型与对应题库
SUPPORTED_MODES: dict[str, list[Question]] = {
    'communication': COMMUNICATION_QUESTIONS,
    'big_five': BIG_FIVE_QUESTIONS,
    'simple': QUESTIONS,
    'full': FULL_QUESTIONS,
    'pdp': PDP_QUESTIONS,
    'mental_age': MENTAL_AGE_QUESTIONS,
}


class QuestionService:
    """题目服务类"""

    def __init__(self) -> None:
        """初始化题目服务,加载题库"""
        self._questions: list[Question] = QUESTIONS

    def _select(self, mode: str) -> list[Question]:
        if mode not in SUPPORTED_MODES:
            raise ValueError("测试模式必须为 simple、full、pdp 或 mental_age")
        return SUPPORTED_MODES[mode]

    def get_all_questions(self, mode: str = "simple") -> list[Question]:
        """获取全部题目(按序号排序)

        Returns:
            题目对象列表
        """
        return self._select(mode)

    def get_total_count(self, mode: str = "simple") -> int:
        """获取题目总数

        Returns:
            题目数量
        """
        return len(self._select(mode))

    def get_question_dicts(self, mode: str = "simple") -> list[dict]:
        """获取全部题目的字典序列化结果(供 API 返回)

        Returns:
            题目字典列表
        """
        return [q.to_dict() for q in self._select(mode)]

    def get_question_by_index(self, index: int, mode: str = "simple") -> Question | None:
        """根据序号获取单个题目

        Args:
            index: 题目序号(1-based)

        Returns:
            题目对象,未找到时返回 None
        """
        for q in self._select(mode):
            if q.index == index:
                return q
        return None

    def validate_answer(self, question_index: int, option_key: str, mode: str = "simple") -> bool:
        """校验某题的答案是否合法

        Args:
            question_index: 题目序号
            option_key: 选项标识(A / B)

        Returns:
            答案是否合法
        """
        question: Question | None = self.get_question_by_index(question_index, mode)
        if question is None:
            return False
        return any(opt.key == option_key for opt in question.options)


# 模块级单例,供控制器层引用
question_service: QuestionService = QuestionService()
