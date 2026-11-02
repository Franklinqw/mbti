"""原创 PDP 风格动物人格题库

以老虎、孔雀、考拉、猫头鹰、变色龙五种动物气质为框架的
二选一情境题,共 20 题:

  - 老虎(TIGER):支配型,目标导向、果断推进
  - 孔雀(PEACOCK):表达型,热情外放、善于感染
  - 考拉(KOALA):耐心型,温和稳定、重视和谐
  - 猫头鹰(OWL):精确型,严谨分析、标准清晰
  - 变色龙(CHAMELEON):整合型,灵活应变、协调各方

计分方式:每个选项归属一种动物,统计各动物被选次数,
取最高者为结果类型;题库保证每种动物恰好出现 8 个选项。
本测试为原创情境题,不是 PDP 官方量表。
"""
from models.questions import Question, Option
from models.results import PersonalityResult

# 五种动物气质代号(计分优先顺序,平局时按此顺序取先出现者)
PDP_SIDES: tuple[str, ...] = ("TIGER", "PEACOCK", "KOALA", "OWL", "CHAMELEON")

# 各动物的展示名称
PDP_NAMES: dict[str, str] = {
    "TIGER": "老虎",
    "PEACOCK": "孔雀",
    "KOALA": "考拉",
    "OWL": "猫头鹰",
    "CHAMELEON": "变色龙",
}

# 题目原始数据:每项为 (题干, 选项A文案, 选项A动物, 选项B文案, 选项B动物)
# 题序按动物交错排列,避免同一种气质连续出现。
_PDP_RAW: list[tuple[str, str, str, str, str]] = [
    ("团队讨论陷入僵局,你更可能:", "直接拍板,先定方向再调整", "TIGER",
     "讲个自己的经历,先把气氛带起来", "PEACOCK"),
    ("收到一份新计划,你先看:", "目标和截止日期是否清晰可执行", "OWL",
     "大家分工之后合作是否顺畅", "KOALA"),
    ("朋友聚会时,你通常是:", "张罗组织、安排流程的那个人", "TIGER",
     "到场就和每个人聊上一圈", "PEACOCK"),
    ("发现某条规则不合理时,你会:", "先按规则执行,再书面提出修改建议", "OWL",
     "看情况灵活处理,别让大家为难", "CHAMELEON"),
    ("你更欣赏哪种同事:", "效率高、说话直接、敢扛事", "TIGER",
     "开朗热心、能把气氛带起来", "PEACOCK"),
    ("项目临时发生变更,你的第一反应:", "有点不安,希望有人解释清楚原因", "KOALA",
     "没关系,顺势调整方案就好", "CHAMELEON"),
    ("群里起了争论,你会:", "出来打个圆场,让双方都有台阶", "CHAMELEON",
     "安静看完全部聊天记录,再谨慎发言", "OWL"),
    ("你更喜欢的工作节奏:", "稳定推进,不喜欢被催促", "KOALA",
     "有挑战、有竞争,越战越有劲", "TIGER"),
    ("汇报工作时你更倾向:", "做一份有故事、有画面的展示", "PEACOCK",
     "一页纸讲清数据和结论", "OWL"),
    ("别人找你帮忙时,你通常:", "不好意思拒绝,先接下来再说", "KOALA",
     "先评估值不值得帮,再明确答复", "TIGER"),
    ("进入新环境,你会:", "很快记住每个人的名字和特点", "PEACOCK",
     "先观察一段时间,摸清情况再行动", "KOALA"),
    ("你更认同的做事方式:", "计划赶不上变化,随机应变最重要", "CHAMELEON",
     "没有规矩不成方圆,标准先行", "OWL"),
    ("轮到你当众发言时,你:", "有点紧张,会根据现场反应调整发挥", "CHAMELEON",
     "正合心意,让大家听到我的想法", "PEACOCK"),
    ("团队里缺少居中调和的角色时:", "你会自然补位,协调各方", "CHAMELEON",
     "你更愿意做踏实执行的后盾", "KOALA"),
    ("购买重要物品时,你更像:", "做表格比参数,反复核对评价", "OWL",
     "相信直觉,喜欢就拿下", "PEACOCK"),
    ("长期任务推进中,你更看重:", "每一步都有人稳稳跟进、不掉队", "KOALA",
     "关键节点敢于冒险突围", "TIGER"),
    ("做决定时,你更依赖:", "逻辑分析和事实核对", "OWL",
     "当下的感受和现场的氛围", "PEACOCK"),
    ("遇到态度强势的人,你会:", "不硬碰,绕一绕也能达成目的", "CHAMELEON",
     "该坚持的立场绝不退让", "TIGER"),
    ("朋友向你吐槽工作,你多半:", "先陪着聊,把情绪接住", "KOALA",
     "直接帮忙分析问题、给方案", "TIGER"),
    ("假期出行,你更喜欢:", "说走就走,路上再调整", "CHAMELEON",
     "提前订好行程,按计划玩", "OWL"),
]


def build_pdp_questions() -> list[Question]:
    """根据原始数据构建 PDP 题目列表

    Returns:
        按 index 排序的题目列表,每题两个选项分属两种动物
    """
    questions: list[Question] = []
    for i, (text, opt_a, side_a, opt_b, side_b) in enumerate(_PDP_RAW, start=1):
        questions.append(Question(index=i, dimension="PDP", text=text, options=[
            Option("A", opt_a, "PDP", side_a),
            Option("B", opt_b, "PDP", side_b),
        ]))
    return questions


# 题目列表(模块级单例,供 Service 层引用)
PDP_QUESTIONS: list[Question] = build_pdp_questions()

# 五种动物的结果描述
PDP_RESULTS: dict[str, PersonalityResult] = {
    "TIGER": PersonalityResult(
        mbti_type="老虎", animal="老虎", emoji="🐯", nickname="支配型",
        traits="目标感强、行动果断,习惯掌控节奏;遇事先定方向,再优化细节。",
        strengths=["决策果断,关键时刻敢拍板", "结果导向,执行力强",
                   "敢于承担责任和风险", "抗压能力强,越有挑战越兴奋"],
        weaknesses=["节奏快,容易显得急躁", "控制欲强,不太愿意放权",
                    "对细节缺乏耐心", "说话直接,偶尔会伤到别人"],
        careers=["项目负责人 / 创业者", "销售或商务负责人",
                 "危机处理与公关", "竞技体育 / 挑战型岗位"]),
    "PEACOCK": PersonalityResult(
        mbti_type="孔雀", animal="孔雀", emoji="🦚", nickname="表达型",
        traits="热情外放、乐观开朗,自带舞台感,走到哪里都能带来能量。",
        strengths=["表达力和感染力强", "自来熟,善于结交和维系人脉",
                   "乐观,情绪恢复得快", "擅长带动气氛、鼓舞士气"],
        weaknesses=["容易冲动,常常先做再想", "关注点多,精力容易分散",
                    "渴望被认可,害怕被忽视", "对细节和后续跟进兴趣不大"],
        careers=["市场 / 品牌运营", "主持、直播与内容创作",
                 "教育培训", "活动策划"]),
    "KOALA": PersonalityResult(
        mbti_type="考拉", animal="考拉", emoji="🐨", nickname="耐心型",
        traits="温和从容、极有耐心,重视关系和谐,是团队里让人安心的存在。",
        strengths=["善于倾听,共情力强", "稳定可靠,值得托付",
                   "能长期坚持做一件事", "天然的团队润滑剂"],
        weaknesses=["不好意思拒绝别人", "回避冲突,容易把话憋在心里",
                    "面对变化比较慢热", "容易委屈自己迁就他人"],
        careers=["人力资源 / 客户成功", "心理支持与咨询方向",
                 "行政与后勤支持", "教育、护理类工作"]),
    "OWL": PersonalityResult(
        mbti_type="猫头鹰", animal="猫头鹰", emoji="🦉", nickname="精确型",
        traits="严谨理性、重视规则与标准,习惯用数据和逻辑说话。",
        strengths=["细节把控力强", "逻辑清晰,分析到位",
                   "标准高,出品可靠", "风险敏感,能提前发现问题"],
        weaknesses=["完美主义,容易过度打磨", "灵活性不足,变通偏慢",
                    "容易挑剔,给身边人压力", "收集信息多,决策偏慢"],
        careers=["财务 / 审计", "数据分析与研究",
                 "法务 / 合规", "研发、测试与质量管理"]),
    "CHAMELEON": PersonalityResult(
        mbti_type="变色龙", animal="变色龙", emoji="🦎", nickname="整合型",
        traits="适应力强、处事圆融,擅长看场合行事,在各方之间灵活周旋。",
        strengths=["协调各方,化解冲突", "应变快,计划之外也能从容",
                   "信息灵通,认识的人面广", "务实中庸,不偏激"],
        weaknesses=["立场不够鲜明", "容易随大流,原则感偏弱",
                    "被多方拉扯,压力往心里去", "有时让人捉摸不透"],
        careers=["项目经理 / 协作型岗位", "商务拓展",
                 "产品经理", "社区与跨部门运营"]),
}
