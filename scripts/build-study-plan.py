"""Build an explicit 180-day study schedule; targets are not inventory claims."""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
course = json.loads((ROOT / 'content/course.json').read_text())
month_specs = [
    dict(title='拼读、基础句式与生活表达', words=800, sentences=1000,
         focus=['字母与问候', '国籍、主格与宾格', '指示、所属与存在', '数字、量词与点单', '位置、距离与收音', '时刻、约定与连音'],
         skills='能自己拼读陌生的韩文音节，完成自我介绍、问路、点单和约时间。',
         reading='世宗学堂入门或初级教材中的同主题短对话；先听音，再核对文字和释义。',
         output='用本日句型写 6–10 句自己的话，并交换角色朗读。前 7 天把其中 30 分钟用于字母组合和听写。',
         checkpoint='随机听写 20 个已学音节，目标至少 18 个正确；不看稿完成 60 秒自我介绍；抽查 30 个已学词，隔天仍能回忆至少 24 个。',
         examMinutes=60),
    dict(title='熟悉日常对话，稳固 TOPIK I 基础', words=1800, sentences=2200,
         focus=['餐饮、敬语与请求', '购物、进行时与尝试', '交通、条件与必要', '约定、比较与承诺', '天气、否定与转述', '症状、过去与起点'],
         skills='听懂生活对话的时间、地点、人物和需求，能连续讲述一段日常经历。',
         reading='世宗学堂初级对话与 TOPIK I 官方公开练习中的通知、广告、生活短文。',
         output='围绕同一情境自编 8–12 轮对话；将现在时改成过去时、肯定改成否定；写 80–120 韩文字的生活记录。',
         checkpoint='完成一套未做过的 TOPIK I 纸笔公开试题，按官方答案核对听力与阅读，训练目标 160/200；逐题解释错误原因。',
         examMinutes=100),
    dict(title='经历、理由与长句，进入 TOPIK II', words=3000, sentences=3800,
         focus=['经历叙述与不规则变化', '计划、愿望与让步', '兴趣、选择与经历句型', '邀请、推测与理由', '比较、建议与名词化', '问题处理、被动与先后'],
         skills='能把时间、原因、条件和结果串成段落，区分敬语、口语与书面表达。',
         reading='世宗学堂中级同主题对话及 TOPIK II 短篇阅读；先标出主句，再找修饰语与连接词。',
         output='把对话改写为 150–250 韩文字的叙述；每次用 3 种已学连接语尾；开始练习 TOPIK II 写作填空与图表说明。',
         checkpoint='完成 TOPIK II 纸笔公开卷的听力、阅读与写作；训练目标总分 120/300。写作按官方尺度请合格韩语教师反馈，未批改时不声称总分达标。',
         examMinutes=180),
    dict(title='社会情境、信息核实与概括', words=4200, sentences=5200,
         focus=['居住、愿望与取舍', '校园讨论与任务分工', '职场、期限与协商', '邮寄、意图与是否', '新闻、间接疑问与推测', '社区讨论与转述建议'],
         skills='能读懂多层修饰句，区分事实、看法与推测，并用自己的话概括信息。',
         reading='世宗学堂中级材料与 TOPIK II 说明类短文；每篇标出主题句、关键词和指代对象。',
         output='将对话改成 200–300 韩文字的说明；先写事实，再写原因与建议；每周完整练一篇图表说明。',
         checkpoint='完成一套未做过的 TOPIK II 纸笔卷，训练目标 150/300；把错题按词汇、语法、主旨、推断与时间不足归因。写作需要外部反馈。',
         examMinutes=180),
    dict(title='抽象观点、让步与论证', words=5200, sentences=6600,
         focus=['环保、制度与代价', '隐私、限制与否定推论', '教育、机会与结果', '老龄化、责任与可持续性', '文化、概括与例外', '工作、条件与政策效果'],
         skills='能比较正反观点，识别论据能支持的范围，写出有让步、有回应的论证。',
         reading='TOPIK II 观点类阅读和世宗学堂高级材料；每次用中文确认逻辑，再用韩语概括。',
         output='同一话题各写一段支持与反对意见，再整理为 600–700 韩文字的论证；每周至少一篇请教师依据评分标准批改。',
         checkpoint='完成一套未做过的 TOPIK II 纸笔卷，训练目标 190/300；复盘写作内容完整性、篇章结构、词汇语法。不得把自己估计的作文分当作实测成绩。',
         examMinutes=180),
    dict(title='综合运用、限时训练与 TOPIK 6 检验', words=6000, sentences=8000,
         focus=['图表、百分比与百分点', '相关、因果与限定表达', '政策、效率与公平', '反论、让步与回应', '研究、引用与责任', '篇章、衔接与文体'],
         skills='在考试时间内完成听力、阅读与写作；能读懂较复杂观点并保持书面语体一致。',
         reading='以未做过的 TOPIK II 官方公开题为主，精读错题对应段落；新词优先选高频遗漏词，不追求偏词数量。',
         output='限时写作并核对题目要求；用 1 分钟口头概括、150 字摘要和完整论证三种方式表达同一内容。',
         checkpoint='在第 170、180 天分别做不同的完整 TOPIK II 纸笔卷，训练目标两次达到 240/300 以上，含得到反馈的写作分。官方 6 级线为 230/300；一次练习达标不等于考试保证。',
         examMinutes=180),
]

styles = [
    ('听懂与拆解', [(45, '听原音', '完整听本关，再逐句重听；先判断谁对谁说、想表达什么。'), (90, '词句理解', '逐个点开句子拆解，辨认原形、助词、时态与语尾；结合词典记录新词的本句义。'), (45, '同主题输入', None), (60, '换角色回应', None)]),
    ('模仿与词形', [(60, '跟读', '以 SunHi 完整句音频为准，分短语跟读，再恢复正常速度；重点模仿停顿、收音与连读。'), (80, '词汇与搭配', '从同主题材料补充新词；每个词连同一个自然句子学习，不用只背孤立中文义。'), (50, '句式变化', '沿用本关语法，变化人称、时间与肯否；对照来源核对变化是否自然。'), (50, '口头与书面回应', None)]),
    ('精听与扩展', [(40, '短句听写', '隐藏中文和拆解，听写本关；逐句核对助词、收音和词形。'), (80, '平行对话', '学习同主题的新对话，逐句对照释义；把熟悉句型在新场景中的用法记下来。'), (60, '阅读与概括', None), (60, '复述与改写', None)]),
    ('迁移与输出', [(60, '脱稿听说', '不看原文复述对话，再换一个角色回答；忘记时先回听完整句子。'), (60, '新词与旧词对比', '补齐当天新词目标，同时区分近义词、搭配对象、语体和常见助词。'), (60, '同主题阅读', None), (60, '完整表达', None)]),
    ('复习与检查', [(60, '主动回忆', '不看中文回忆本周期词句；抽测隔天、3 天、7 天前学过的内容，记录正确率。'), (60, '听写与回听', '隐藏韩文听写本关，再对照原文定位听不出的音节；回听完整句确认。'), (60, '综合输出', None), (60, '纠错与调整', '只复习，不增加词句配额。检查译义、助词、时态与衔接；回忆正确率低于 80% 时，把下一周期新内容减半。')]),
]

days, months = [], []
prev_words = prev_sentences = 0
for m, spec in enumerate(month_specs):
    months.append(dict(month=m+1, startDay=m*30+1, endDay=(m+1)*30, **spec))
    new_index = 0
    for d in range(1, 31):
        cycle, phase = (d-1)//5, (d-1)%5
        title, template = styles[phase]
        lesson = course[m*6+cycle]
        day = m*30+d
        before = new_index
        if phase < 4:
            new_index += 1
        words = ((spec['words']-prev_words)*new_index//24 - (spec['words']-prev_words)*before//24)
        sentences = ((spec['sentences']-prev_sentences)*new_index//24 - (spec['sentences']-prev_sentences)*before//24)
        tasks=[]
        for index, (minutes, name, instruction) in enumerate(template):
            if instruction is None:
                instruction = spec['output'] if index==len(template)-1 or phase==4 else spec['reading']
            tasks.append(dict(minutes=minutes, title=name, instruction=instruction))
        assessment = None
        if d==30 or (m==5 and d==20):
            assessment=spec['checkpoint']
            minutes=spec['examMinutes']
            tasks=[dict(minutes=minutes,title='月末测评' if d==30 else '第一次完整检验',instruction=assessment), dict(minutes=240-minutes,title='核对、归因与下阶段调整',instruction='逐项记录证据和薄弱点；客观题按官方答案核对，作文等待按评分标准的反馈。若未达到本月训练目标，先补短板，再调整进度。')]
        days.append(dict(day=day,month=m+1,lessonId=lesson['id'],topic=spec['focus'][cycle],title=title if not assessment else '限时测评与复盘',newWords=words,newSentences=sentences,cumulativeWords=prev_words+(spec['words']-prev_words)*new_index//24,cumulativeSentences=prev_sentences+(spec['sentences']-prev_sentences)*new_index//24,minutes=240,tasks=tasks,assessment=assessment))
    prev_words,prev_sentences=spec['words'],spec['sentences']

plan=dict(days=days,months=months,totalDays=180,dailyMinutes=240,totalHours=720,
    inventoryNote='日程以站内 36 段对话作精读锚点，并配合同主题官方学习材料与公开题扩展。6,000 词条、8,000 个不同句子是学习输入目标，包含站外材料；不是站内已经收录的数量，也不是 TOPIK 官方门槛。',
    retentionRule='每 5 天安排一天复习。复习同一句不增加独立句数；同一词形的屈折变化不重复计算词条。隔天回忆低于 80% 时减少新内容，不为了完成数量跳过理解。',
    sources=[dict(label='国立国语院韩中词典',url='https://krdict.korean.go.kr/'),dict(label='世宗学堂学习平台',url='https://nuri.iksi.or.kr/'),dict(label='TOPIK 官方网站与公开学习资料',url='https://www.topik.go.kr/'),dict(label='NIIED 官方考试说明',url='https://www.niied.go.kr/web/NIIED/contents/niiedEng/eng_topikOverview')])
assert len(days)==180 and [d['day'] for d in days]==list(range(1,181))
assert sum(d['newWords'] for d in days)==6000 and sum(d['newSentences'] for d in days)==8000
assert all(sum(t['minutes'] for t in d['tasks'])==240 for d in days)
(ROOT/'content/study-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
markdown=['# 180 天韩语对话学习计划','', '每天 4 小时，共 720 小时。可自由选择任何关卡，日程是建议顺序。','',plan['inventoryNote'],'',plan['retentionRule'],'']
for month in months:
    markdown += [f"## 第 {month['month']} 月 · {month['title']}",'',month['skills'],'',f"累计输入目标：{month['words']:,} 词条 / {month['sentences']:,} 个不同句子。",'']
    for day in days[(month['month']-1)*30:month['month']*30]:
        lesson=next(l for l in course if l['id']==day['lessonId'])
        markdown += [f"### 第 {day['day']} 天 · {day['topic']} · {day['title']}",'',f"站内锚点：{lesson['title']}。本日新增目标 {day['newWords']} 词条 / {day['newSentences']} 句（包含站外学习材料）。",'']
        markdown += [f"- {t['minutes']} 分钟 · {t['title']}：{t['instruction']}" for t in day['tasks']]
        markdown += ['']
markdown += ['## 来源与使用方式','']+[f"- [{s['label']}]({s['url']})" for s in plan['sources']]+['','学习目标不保证半年从零达到 TOPIK 6。最终以完整限时测评、写作反馈与正式考试为准。','']
(ROOT/'docs/180-day-plan.md').write_text('\n'.join(markdown))
print(json.dumps({'days':len(days),'hours':720,'targetWords':6000,'targetSentences':8000,'anchorLessons':len(course)},ensure_ascii=False))
