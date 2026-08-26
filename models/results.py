"""MBTI 结果数据模块

定义 16 种 MBTI 人格类型与对应动物的映射关系,
包含动物形象、性格特点、优势、建议等结果描述信息。

需求文档指定:INTJ 对应猫头鹰,其余 15 种类型按性格特征匹配动物。
"""
from typing import NamedTuple


class PersonalityResult(NamedTuple):
    """人格类型结果"""

    mbti_type: str        # MBTI 类型代号,如 INTJ
    animal: str           # 对应动物名称,如 猫头鹰
    emoji: str            # 动物 emoji,用于前端展示
    nickname: str         # 类型昵称,如 战略家
    traits: str           # 性格特点描述
    strengths: list[str]  # 优势列表
    weaknesses: list[str] # 劣势列表
    careers: list[str]    # 适合的职业方向


# 16 种 MBTI 类型的结果数据
RESULTS: list[PersonalityResult] = [
    PersonalityResult(
        mbti_type="INTJ",
        animal="猫头鹰",
        emoji="🦉",
        nickname="战略家",
        traits="冷静独立,目光长远,擅长系统化思考与战略规划。"
               "内心有清晰的目标蓝图,做事专注,追求高效与完美。",
        strengths=["全局视野与战略思维", "独立自主,意志坚定", "逻辑严密,洞察力强"],
        weaknesses=["有时过于追求完美", "情感表达相对含蓄", "对低效事物缺乏耐心"],
        careers=["战略顾问", "科研学者", "系统架构师"],
    ),
    PersonalityResult(
        mbti_type="INTP",
        animal="猫",
        emoji="🐱",
        nickname="思考者",
        traits="充满好奇心,喜欢探索抽象概念与理论原理。"
               "思维灵活跳跃,善于发现事物间的逻辑联系,享受独自钻研的乐趣。",
        strengths=["逻辑分析能力出色", "求知欲旺盛", "思想开放,富有创意"],
        weaknesses=["行动力有时不足", "对琐事容易厌倦", "社交主动性较低"],
        careers=["科研人员", "软件工程师", "理论分析师"],
    ),
    PersonalityResult(
        mbti_type="ENTJ",
        animal="狮子",
        emoji="🦁",
        nickname="指挥官",
        traits="天生具备领导气质,果断有魄力,善于统筹全局。"
               "目标明确,执行力强,能带领团队高效达成目标。",
        strengths=["领导与决策能力强", "目标坚定,执行力高", "善于统筹规划"],
        weaknesses=["有时过于强势", "对效率低难以容忍", "情感细腻度有待提升"],
        careers=["企业高管", "项目经理", "创业者"],
    ),
    PersonalityResult(
        mbti_type="ENTP",
        animal="狐狸",
        emoji="🦊",
        nickname="辩论家",
        traits="机智敏锐,思维敏捷,热爱思辨与创新。"
               "总能从新颖角度看问题,善于发现机会,享受智力交锋的乐趣。",
        strengths=["创新思维出众", "反应敏捷,口才好", "适应能力强"],
        weaknesses=["容易三分钟热度", "有时过于好辩", "对常规事务缺乏耐心"],
        careers=["创业者", "律师", "产品经理"],
    ),
    PersonalityResult(
        mbti_type="INFJ",
        animal="狼",
        emoji="🐺",
        nickname="提倡者",
        traits="内心深邃,富有理想主义与洞察力。"
               "安静而坚定,关心他人与世界的深层意义,默默为信念付诸行动。",
        strengths=["洞察力与共情力强", "理想坚定,有使命感", "善于倾听与启发"],
        weaknesses=["容易自我内耗", "对冲突较为敏感", "完美主义倾向"],
        careers=["心理咨询师", "作家", "公益组织者"],
    ),
    PersonalityResult(
        mbti_type="INFP",
        animal="鹿",
        emoji="🦌",
        nickname="调停者",
        traits="温柔善良,内心充满理想与诗意。"
               "重视真诚与价值观,富有创造力与想象力,追求内心的和谐与美好。",
        strengths=["创造力与想象力丰富", "真诚善良,共情力强", "忠于内心价值观"],
        weaknesses=["容易理想化现实", "对批评较为敏感", "决断力有时不足"],
        careers=["作家", "艺术家", "心理咨询师"],
    ),
    PersonalityResult(
        mbti_type="ENFJ",
        animal="海豚",
        emoji="🐬",
        nickname="主人公",
        traits="温暖热情,善于感染与带动他人。"
               "天生的沟通者与组织者,关注团队成长,乐于助人实现潜能。",
        strengths=["沟通与感染力强", "善于组织与激励", "富有同理心与责任感"],
        weaknesses=["有时忽略自身需求", "对他人评价敏感", "容易过度付出"],
        careers=["教师", "团队领导", "人力资源"],
    ),
    PersonalityResult(
        mbti_type="ENFP",
        animal="小狗",
        emoji="🐶",
        nickname="竞选者",
        traits="热情开朗,充满好奇心与生命力。"
               "思维活跃,善于发现生活中的可能性,与人相处真诚而富有感染力。",
        strengths=["热情洋溢,感染力强", "好奇心与创造力旺盛", "善于人际交往"],
        weaknesses=["注意力易分散", "有时缺乏条理", "对压力较为敏感"],
        careers=["创意策划", "市场营销", "记者"],
    ),
    PersonalityResult(
        mbti_type="ISTJ",
        animal="蜜蜂",
        emoji="🐝",
        nickname="物流师",
        traits="踏实可靠,做事严谨有计划。"
               "尊重事实与传统,重视秩序与责任,是值得信赖的执行者。",
        strengths=["责任心强,踏实可靠", "做事有条不紊", "注重事实与细节"],
        weaknesses=["对变化适应较慢", "不够灵活变通", "情感表达较为内敛"],
        careers=["会计师", "审计师", "行政管理"],
    ),
    PersonalityResult(
        mbti_type="ISFJ",
        animal="袋鼠",
        emoji="🦘",
        nickname="守卫者",
        traits="温和细心,默默守护身边的人。"
               "善于照顾他人,重视和谐与稳定,是体贴而可靠的伙伴。",
        strengths=["细心体贴,富有责任感", "耐心且善于照顾人", "忠诚可靠"],
        weaknesses=["不善拒绝他人", "容易压抑自身需求", "对变化较为保守"],
        careers=["护士", "幼师", "客户服务"],
    ),
    PersonalityResult(
        mbti_type="ESTJ",
        animal="鹰",
        emoji="🦅",
        nickname="总经理",
        traits="务实果断,善于管理与执行。"
               "重视秩序、规则与效率,办事雷厉风行,是出色的组织管理者。",
        strengths=["组织与执行能力强", "果断务实,讲求效率", "责任心与原则性强"],
        weaknesses=["有时过于强势", "对情感关注不足", "灵活性有待提升"],
        careers=["管理者", "公务员", "运营主管"],
    ),
    PersonalityResult(
        mbti_type="ESFJ",
        animal="海狸",
        emoji="🦫",
        nickname="执政官",
        traits="热心友善,重视人际和谐与合作。"
               "善于照顾他人感受,乐于营造温暖的氛围,是团队的凝聚力所在。",
        strengths=["热情友善,乐于助人", "善于营造和谐氛围", "责任心与协作力强"],
        weaknesses=["对他人评价敏感", "不善处理冲突", "有时过于在意他人看法"],
        careers=["人力资源", "活动策划", "医护服务"],
    ),
    PersonalityResult(
        mbti_type="ISTP",
        animal="鲨鱼",
        emoji="🦈",
        nickname="鉴赏家",
        traits="冷静务实,行动力强。"
               "善于动手实践与解决实际问题,独立而高效,喜欢探索事物的运作方式。",
        strengths=["动手与实操能力强", "冷静理性,临场反应快", "独立高效"],
        weaknesses=["不善表达情感", "对规则约束不耐烦", "长期规划意识较弱"],
        careers=["工程师", "机械师", "急救人员"],
    ),
    PersonalityResult(
        mbti_type="ISFP",
        animal="考拉",
        emoji="🐨",
        nickname="探险家",
        traits="温和随性,富有艺术气质。"
               "重视当下体验与内心感受,审美敏锐,享受以自己的节奏生活。",
        strengths=["审美与艺术感受力强", "温和体贴,善解人意", "灵活随性"],
        weaknesses=["长远规划意识较弱", "不擅长冲突与压力", "决断力不足"],
        careers=["设计师", "艺术家", "兽医"],
    ),
    PersonalityResult(
        mbti_type="ESTP",
        animal="猎豹",
        emoji="🐆",
        nickname="企业家",
        traits="果敢敏捷,充满行动力。"
               "善于把握当下机会,反应迅速,喜欢充满挑战与变化的环境。",
        strengths=["行动力与决断力强", "临场应变能力出色", "善于把握机会"],
        weaknesses=["对长期规划缺乏耐心", "容易冲动", "对规则约束不适"],
        careers=["销售", "创业者", "运动员"],
    ),
    PersonalityResult(
        mbti_type="ESFP",
        animal="猴子",
        emoji="🐵",
        nickname="表演者",
        traits="活泼开朗,充满感染力。"
               "热爱生活,善于享受当下,是人群中的开心果与气氛担当。",
        strengths=["热情开朗,感染力强", "善于活跃气氛", "观察与应变力出色"],
        weaknesses=["容易三分钟热度", "长期规划意识弱", "对压力较为敏感"],
        careers=["演员", "活动主持", "旅游策划"],
    ),
]


# 以 MBTI 类型为键的快速查询字典
RESULT_MAP: dict[str, PersonalityResult] = {r.mbti_type: r for r in RESULTS}
