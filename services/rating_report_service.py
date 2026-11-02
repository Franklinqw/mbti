"""评分解释为本项目自编；0–100 是量程换算，不是人群百分位。"""
CONTENT={
'DIRECT':('你可能更习惯间接表达或先观察气氛。','你较常清楚表达需求并推动讨论。','用“我需要……，你是否愿意……”替代指责；明确表达也要为对方留回应空间。'),
'LISTEN':('你可能更快进入回应或解决问题环节。','你较常先理解对方的感受和重点。','先复述一句“你的意思是……吗”，确认理解后，也说出自己的需要。'),
'ANALYZE':('你可能更依赖当下感受和直观判断。','你较常核对事实、背景与方案条件。','把事实与推测分别写下；核对信息时避免让沟通变成审问。'),
'PAUSE':('你可能偏好立即回应，暂停讨论较不自然。','你较常利用停顿整理思路和情绪。','需要暂停时说明原因，并约定继续沟通的具体时间，避免暂停变成长期失联。'),
'E':('你可能更偏好安静、小范围互动和独处。','你可能更享受主动交流与群体互动。','根据自己的精力安排交流和独处，重要沟通可以提前准备要点。'),
'A':('你可能更直接、审慎，较重视自己的立场。','你可能更体谅他人，愿意合作和照顾感受。','同时表达体谅与边界：合作不等于凡事答应，坚持立场也可以保持尊重。'),
'C':('你可能更灵活随性，固定计划较不自然。','你可能更重视组织、细节与完成承诺。','为重要任务保留一个最小清单，也为意外情况和休息留出余量。'),
'S':('你的自述可能显示近期更容易有压力感和情绪波动。','你的自述可能显示较常放松、情绪较平稳。','留意睡眠、负荷与情境变化；本维度不能用于判断是否存在心理疾病。'),
'O':('你可能更偏好具体熟悉的信息和务实表达。','你可能更喜欢抽象想法、想象和思考。','尝试一个小的新体验，并把想法转成具体步骤；该维度不是智力测验。')}

def build_rating_report(dimensions, mode):
    communication=mode=='communication'
    insights=[]
    for key,value in dimensions.items():
        low,high,action=CONTENT[key]
        level='较低区间' if value['percent']<40 else '较高区间' if value['percent']>60 else '中间区间'
        description=low if value['percent']<40 else high if value['percent']>60 else '本次作答位于量程中段，可能包含不同情境下的表现，或对部分问题尚不确定；可结合具体经历理解。'
        insights.append({'label':value['label'],'level':level,'description':description,'action':action})
    method=('原创沟通风格自我探索问卷；请按最近一个月的通常表现作答，四个维度可同时较高或较低。本问卷尚未进行标准化验证。' if communication else
            '题目依据公共领域 IPIP Big-Five Factor Markers（每维10题），采用本项目中文工作译文；中文版本和本报告解释尚未经过独立信效度验证。情绪维度以情绪稳定性正向呈现。')
    method+=' 图中数值是原始分量程换算，不是人群百分位、能力分数或各维度占比；40/60分界只用于本页描述，不是常模或诊断界限。'
    return {'mbtiType':'COMM' if communication else 'BIG5','title':'我的沟通画像' if communication else '我的大五画像',
            'nickname':'沟通风格' if communication else '大五人格','animal':'四维探索' if communication else '五维探索',
            'emoji':'💬' if communication else '🌿','dimensionKind':'scale','dimensions':dimensions,
            'traits':'不同情境下，你可以使用不止一种沟通方式；这些分数描述本次自述，不是好坏排名。' if communication else '五个维度共同构成你的性格画像。不同倾向各有适用情境，得分不能换算成 MBTI 类型或智力水平。',
            'strengths':[f'{i["label"]}：{i["description"]}' for i in insights],
            'weaknesses':[f'{i["label"]}：{i["action"]}' for i in insights],
            'careers':['练习清楚表达一次需求','练习复述对方观点','分歧升温时约定暂停与重谈'] if communication else ['观察不同情境中的自己','每周记录一次有效习惯','选择一项小而具体的成长练习'],
            'insights':insights,'methodNote':method,
            'sourceUrl':None if communication else 'https://ipip.ori.org/newBigFive5broadKey.htm',
            'questionnaireVersion':'communication-1' if communication else 'ipip50-zh-working-1'}
