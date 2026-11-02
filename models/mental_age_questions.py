"""原创心理年龄题库

轻松趣味向的自我探索题,共 15 题。每个选项带有 1–5 的"成熟度"
分值与一种作答风格集群,总分线性映射到 12–60 岁的心理年龄,
再落入五个气质分段(每种分段配一种动物形象)。

  - 童心能量(PLAY):好奇心、玩心与直接的快乐
  - 好奇探索(CURIOS):对新鲜事物的开放度
  - 温和稳重(STEADY):从容、体谅与情绪承接
  - 自律秩序(DISCIPL):计划、规律与自我要求

本测试为娱乐向原创问卷,不是心理发展评估工具。
"""
from models.questions import Question, Option
from models.results import PersonalityResult

# 风格集群代号与展示名称
AGE_CLUSTERS: tuple[str, ...] = ("PLAY", "CURIOS", "STEADY", "DISCIPL")
CLUSTER_LABELS: dict[str, str] = {
    "PLAY": "童心能量",
    "CURIOS": "好奇探索",
    "STEADY": "温和稳重",
    "DISCIPL": "自律秩序",
}

# 心理年龄的输出区间
AGE_MIN, AGE_MAX = 12, 60

# 题目原始数据:每项为
# (题干, 年轻向文案, 年轻向集群, 年轻向分值, 成熟向文案, 成熟向集群, 成熟向分值)
# 构建时按题号交替 A / B 顺序,避免固定选 A 总落在同一方向。
_MENTAL_AGE_RAW: list[tuple[str, str, str, int, str, str, int]] = [
    ("路过小学门口的文具店,你会:", "还是想进去逛一圈,买点贴纸", "PLAY", 1,
     "想到家里已经有很多,直接走开", "DISCIPL", 4),
    ("周末早上自然醒来,你通常:", "先躺着刷一会儿手机再说", "PLAY", 2,
     "起床、吃早餐,开始一天的安排", "DISCIPL", 4),
    ("突然收到一笔小奖金,你会:", "马上想好怎么犒劳自己", "PLAY", 2,
     "先存起来,再慢慢规划用途", "STEADY", 4),
    ("学一样新东西时,你更像:", "三分钟热度,好玩就行", "CURIOS", 2,
     "定好计划,一步一步练扎实", "DISCIPL", 5),
    ("朋友深夜情绪低落找你,你会:", "陪他聊到情绪过去", "STEADY", 3,
     "发点好玩的图和段子逗他笑", "PLAY", 3),
    ("你更认同的说法:", "「长大」是选项,不是必选项", "PLAY", 3,
     "长大就是学会承担责任", "DISCIPL", 4),
    ("你的衣柜更接近:", "彩色联名款和有趣印花", "PLAY", 2,
     "基础耐穿款,怎么搭都不出错", "DISCIPL", 4),
    ("菜单上出现没见过的菜,你会:", "很好奇,想点来试试", "CURIOS", 1,
     "先看看大家评价,稳一点", "STEADY", 3),
    ("原定计划被打乱时,你会:", "顺势换个安排,也不错", "PLAY", 3,
     "心里会乱一下,然后重新排计划", "DISCIPL", 4),
    ("你的收藏夹里更多是:", "搞笑视频和萌宠", "PLAY", 1,
     "纪录片和硬核新知", "CURIOS", 5),
    ("理想的旅行方式:", "走到哪算哪,惊喜最重要", "CURIOS", 2,
     "攻略做到小时级,心里踏实", "DISCIPL", 5),
    ("房间的常态是:", "「乱中有序」,自己舒服就行", "PLAY", 2,
     "每天固定时间整理归位", "DISCIPL", 5),
    ("新出的应用或网络热梗,你会:", "第一时间上手玩", "CURIOS", 1,
     "等热度稳定了再说", "STEADY", 4),
    ("睡前那一刻,你常常:", "「再刷五分钟」变成一小时", "PLAY", 2,
     "到点放下手机,明天还有安排", "DISCIPL", 4),
    ("朋友更可能这样形容你:", "「跟你待着特别轻松」", "PLAY", 3,
     "「把事情交给你很放心」", "STEADY", 4),
]


def build_mental_age_questions() -> list[Question]:
    """根据原始数据构建心理年龄题目列表

    Returns:
        按 index 排序的题目列表,选项顺序按题号交替
    """
    questions: list[Question] = []
    for i, (text, young_t, young_c, young_s, mature_t, mature_c, mature_s) in enumerate(
            _MENTAL_AGE_RAW, start=1):
        young = Option("A", young_t, "AGE", young_c, score=young_s)
        mature = Option("B", mature_t, "AGE", mature_c, score=mature_s)
        # 奇数题 A=年轻向,偶数题交换,避免固定选 A 总偏向同一端。
        pair = [young, mature] if i % 2 == 1 else [mature, young]
        pair[0].key, pair[1].key = "A", "B"
        questions.append(Question(index=i, dimension="AGE", text=text, options=pair))
    return questions


# 题目列表(模块级单例,供 Service 层引用)
MENTAL_AGE_QUESTIONS: list[Question] = build_mental_age_questions()

# 全选年轻向 / 成熟向时的总分,用于线性映射到年龄区间
MENTAL_AGE_SCORE_MIN: int = sum(
    min(opt.score for opt in q.options) for q in MENTAL_AGE_QUESTIONS)
MENTAL_AGE_SCORE_MAX: int = sum(
    max(opt.score for opt in q.options) for q in MENTAL_AGE_QUESTIONS)

# 心理年龄分段:(下界, 上界, 结果描述),自低到高排列
MENTAL_AGE_BANDS: list[tuple[int, int, PersonalityResult]] = [
    (12, 17, PersonalityResult(
        mbti_type="灵魂小孩", animal="小鹿", emoji="🦌", nickname="灵魂小孩",
        traits="你的内心住着一个精力充沛的小孩,快乐来得直接,好奇心从不打烊。",
        strengths=["好奇心旺盛,什么都想试试", "快乐阈值低,容易被小事情打动",
                   "想象力丰富,脑洞层出不穷", "真诚不设防,天然讨人喜欢"],
        weaknesses=["容易三分钟热度", "对枯燥的事情没什么耐心",
                    "延迟满足的能力还有限"],
        careers=["保留一项「无目的」的纯粹爱好", "和稳重的朋友搭伙做正事",
                 "把兴趣清单拆成小目标逐个点亮"])),
    (18, 24, PersonalityResult(
        mbti_type="元气青年", animal="柯基", emoji="🐶", nickname="元气青年",
        traits="电量满格、社交在线,对世界保持着旺盛的热情和行动力。",
        strengths=["行动力强,说做就做", "学新东西上手很快",
                   "社交能量足,到哪里都能聊起来", "恢复力好,睡一觉就满血复活"],
        weaknesses=["容易熬夜透支精力", "注意力容易被新鲜事带走",
                    "冲动消费指数偏高"],
        careers=["把大目标拆成小关卡逐个通关", "给周末留一天空白用来恢复",
                 "记账,或给购物车设一个冷静期"])),
    (25, 31, PersonalityResult(
        mbti_type="轻熟灵魂", animal="狐狸", emoji="🦊", nickname="轻熟灵魂",
        traits="在成熟与天真之间切换自如,知道什么时候该认真,什么时候可以放松。",
        strengths=["情绪趋于稳定,收放自如", "懂得取舍,不再事事较劲",
                   "能兼顾责任和自己的兴趣", "对别人多了一份体谅"],
        weaknesses=["偶尔陷入自我比较和内耗", "想得比做得多的时刻不少",
                    "对「应该」两个字越来越敏感"],
        careers=["减少和别人的人生进度条对比", "定期清理不再重要的目标",
                 "保留一项能沉浸进去的爱好"])),
    (32, 44, PersonalityResult(
        mbti_type="成熟内核", animal="陆龟", emoji="🐢", nickname="成熟内核",
        traits="稳重从容、情绪波动小,是朋友心里那根「定海神针」。",
        strengths=["靠谱,答应的事一定办到", "长期主义者,耐得住性子",
                   "抗压能力强,遇到事情先稳住", "能接得住别人的情绪"],
        weaknesses=["对新变化的适应偏慢", "容易把风险想得过多",
                    "偶尔忘了给自己松绑"],
        careers=["每月做一件没做过的小事", "练习说「随便试试」",
                 "把散步和发呆正式排进日程"])),
    (45, 60, PersonalityResult(
        mbti_type="岁月智者", animal="大象", emoji="🐘", nickname="岁月智者",
        traits="像一位温和的老灵魂,看得透,也放得下。",
        strengths=["洞察力强,常常一眼看到本质", "情绪自洽,不轻易被带节奏",
                   "看得长远,不被一时得失困住", "给人稳稳的安全感"],
        weaknesses=["对新鲜事物慢半拍", "偶尔显得淡漠疏离",
                    "藏着隐隐的说教倾向"],
        careers=["主动接触年轻人的文化和梗", "保持一项规律的运动",
                 "把阅历写下来,分享给别人"])),
]


def band_for_age(age: int) -> PersonalityResult:
    """根据心理年龄返回所在分段的结果描述

    Args:
        age: 心理年龄(岁)

    Returns:
        所在分段的 PersonalityResult

    Raises:
        ValueError: 年龄超出题库输出区间时抛出
    """
    for low, high, result in MENTAL_AGE_BANDS:
        if low <= age <= high:
            return result
    raise ValueError(f"心理年龄超出范围: {age}")
