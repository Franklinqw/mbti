"""MBTI 题库数据模块

围绕 MBTI 四个维度设计共 20 道测试题目:
  - 外向(E)/内向(I):5 题
  - 感觉(S)/直觉(N):5 题
  - 思考(T)/情感(F):5 题
  - 判断(J)/知觉(P):5 题

每道题目包含两个选项,分别对应同一维度的两种倾向。
"""
from typing import Literal

# MBTI 四个维度定义
Dimension = Literal["EI", "SN", "TF", "JP"]

# 各维度两端的字母代号
DIMENSION_LETTERS: dict[str, tuple[str, str]] = {
    "EI": ("E", "I"),  # 外向 / 内向
    "SN": ("S", "N"),  # 感觉 / 直觉
    "TF": ("T", "F"),  # 思考 / 情感
    "JP": ("J", "P"),  # 判断 / 知觉
}

# 维度中文名称
DIMENSION_NAMES: dict[str, tuple[str, str]] = {
    "EI": ("外向", "内向"),
    "SN": ("感觉", "直觉"),
    "TF": ("思考", "情感"),
    "JP": ("判断", "知觉"),
}


class Option:
    """题目选项"""

    def __init__(self, key: str, text: str, dimension: str, side: str,
                 score: int = 1) -> None:
        """初始化题目选项

        Args:
            key: 选项标识(A / B)
            text: 选项文案
            dimension: 所属维度(EI / SN / TF / JP,或其他测试的分组键)
            side: 维度端点字母(E / I / S / N / T / F / J / P),或其他测试的计分桶
            score: 选项分值,供累加型计分使用,对立二选一测试用默认值
        """
        self.key: str = key
        self.text: str = text
        self.dimension: str = dimension
        self.side: str = side
        self.score: int = score

    def to_dict(self) -> dict:
        """转换为字典(供 API 序列化)"""
        return {
            "key": self.key,
            "text": self.text,
        }


class Question:
    """测试题目"""

    def __init__(self, index: int, dimension: Dimension, text: str,
                 options: list[Option]) -> None:
        """初始化题目

        Args:
            index: 题目序号(1-based)
            dimension: 所属维度
            text: 题干文案
            options: 选项列表
        """
        self.index: int = index
        self.dimension: str = dimension
        self.text: str = text
        self.options: list[Option] = options

    def to_dict(self) -> dict:
        """转换为字典(供 API 序列化,选项中不暴露维度信息)"""
        return {
            "index": self.index,
            "dimension": self.dimension,
            "text": self.text,
            "options": [opt.to_dict() for opt in self.options],
        }


# 题目原始数据定义:每项为 (题干, 维度, [(选项文案, 端点字母), ...])
_QUESTIONS_RAW: list[tuple[str, Dimension, list[tuple[str, str]]]] = [
    # ============ 外向(E)/内向(I) ============
    ("在聚会中,你通常更倾向于:", "EI", [
        ("主动与许多人交流,包括刚认识的陌生人", "E"),
        ("只和熟悉的人小范围交流,保持安静", "I"),
    ]),
    ("周末有空闲时间,你更希望:", "EI", [
        ("约上朋友一起外出活动", "E"),
        ("独自待在家看书或做自己的事情", "I"),
    ]),
    ("你觉得自己的能量更多来源于:", "EI", [
        ("与他人互动交流的热闹", "E"),
        ("独处时内心的思考与沉淀", "I"),
    ]),
    ("在团队讨论中,你通常:", "EI", [
        ("积极发言,边说边整理思路", "E"),
        ("先在心里想清楚,再谨慎发言", "I"),
    ]),
    ("面对刚认识的人,你通常:", "EI", [
        ("很快就能熟络,主动找话题", "E"),
        ("需要一段时间才能慢慢打开心扉", "I"),
    ]),

    # ============ 感觉(S)/直觉(N) ============
    ("你更感兴趣的是:", "SN", [
        ("实际发生的事实和具体细节", "S"),
        ("事物背后的可能性与深层关联", "N"),
    ]),
    ("做决定时,你更看重:", "SN", [
        ("过往经验和当下的现实情况", "S"),
        ("未来趋势与事物潜在的意义", "N"),
    ]),
    ("阅读一段文字时,你更关注:", "SN", [
        ("作者字面表达的具体信息", "S"),
        ("文字背后隐含的深层含义", "N"),
    ]),
    ("向别人描述一件事时,你更倾向:", "SN", [
        ("具体准确地说明每个细节", "S"),
        ("概括性地讲清大致意思", "N"),
    ]),
    ("你更愿意相信:", "SN", [
        ("亲眼所见、亲身经历的事实", "S"),
        ("自己的直觉和灵感预感", "N"),
    ]),

    # ============ 思考(T)/情感(F) ============
    ("朋友遇到困难找你倾诉,你会:", "TF", [
        ("帮他分析问题并给出解决方案", "T"),
        ("先安慰他的情绪,给予情感支持", "F"),
    ]),
    ("做决定时,你更依赖:", "TF", [
        ("逻辑分析和客观标准", "T"),
        ("个人价值观和他人的感受", "F"),
    ]),
    ("你认为更重要的事情是:", "TF", [
        ("公平公正,一视同仁", "T"),
        ("和谐融洽,照顾每个人的感受", "F"),
    ]),
    ("需要指出别人问题时,你更注重:", "TF", [
        ("直接说清问题,对事不对人", "T"),
        ("委婉表达,尽量避免伤害对方", "F"),
    ]),
    ("你更欣赏这样的人:", "TF", [
        ("理性冷静、能力出众", "T"),
        ("热情温暖、善解人意", "F"),
    ]),

    # ============ 判断(J)/知觉(P) ============
    ("你的生活作息和工作方式更接近:", "JP", [
        ("有计划有清单,按部就班地推进", "J"),
        ("灵活随性,根据情况见机行事", "P"),
    ]),
    ("面对截止日期,你通常:", "JP", [
        ("提前规划,尽早完成才安心", "J"),
        ("在压力下更有干劲,临近时发力", "P"),
    ]),
    ("你的桌面和房间通常:", "JP", [
        ("整洁有序,物品各有归处", "J"),
        ("看似凌乱,但自己心中有数", "P"),
    ]),
    ("出门旅行时你更喜欢:", "JP", [
        ("提前定好行程和酒店", "J"),
        ("随性而行,走到哪算哪", "P"),
    ]),
    ("对于规则和计划,你:", "JP", [
        ("认为应当遵守并认真执行", "J"),
        ("觉得可以灵活调整和变通", "P"),
    ]),
]


def build_questions() -> list[Question]:
    """根据原始数据构建题目对象列表

    Returns:
        按 index 排序的题目列表
    """
    questions: list[Question] = []
    for i, (text, dimension, opts_raw) in enumerate(_QUESTIONS_RAW, start=1):
        options: list[Option] = []
        for j, (opt_text, side) in enumerate(opts_raw):
            key: str = chr(ord("A") + j)  # A / B
            options.append(Option(key=key, text=opt_text,
                                   dimension=dimension, side=side))
        questions.append(Question(index=i, dimension=dimension,
                                  text=text, options=options))
    return questions


# 题目列表(模块级单例,供 Service 层引用)
QUESTIONS: list[Question] = build_questions()
