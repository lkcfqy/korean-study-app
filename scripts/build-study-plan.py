"""Build 180 days from the actual in-site inventory; counts never include external content."""
from course_data import load_course
import json,pathlib,re
from course_keys import sentence_key
ROOT=pathlib.Path(__file__).resolve().parents[1]
course=load_course()
months=json.loads((ROOT/'content/month-specs.json').read_text())
seen_words,seen_sentences=set(),set()
days=[]
for day in range(1,181):
    assigned=[l for l in course if l['day']==day]
    old_words,old_sentences=len(seen_words),len(seen_sentences)
    for lesson in assigned:
        for line in lesson['lines']:
            seen_sentences.add(sentence_key(line['ko']))
            seen_words.update(w['term'] for w in line['words'])
    month=(day-1)//30
    review=day%5==0
    ids=[l['id'] for l in assigned]
    groups=[]
    recent_days=list(range(max(1,day-4),day)) if review else [day-1]
    for label,source_days in [('近期回忆',recent_days),('一周后再遇见',[day-7]),('一个月后再遇见',[day-30])]:
        group_ids=[l['id'] for l in course if l['day'] in source_days]
        already={identity for group in groups for identity in group['lessonIds']}
        group_ids=[identity for identity in group_ids if identity not in already]
        if group_ids:groups.append(dict(title=label,lessonIds=group_ids))
    review_ids=[identity for group in groups for identity in group['lessonIds']]
    review_rows=sum(len(l['lines']) for l in course if l['id'] in set(review_ids))
    if review:
        tasks=[dict(minutes=60,title='不看中文回忆',instruction='复习前四天的站内对话，先说出大意，再显示中文核对人物、时态、否定和条件。'),dict(minutes=60,title='精听与听写',instruction='听完整的 SunHi 句子，写出韩文，再点开词语检查收音、助词与变形。'),dict(minutes=60,title='换角色回应',instruction='交换对话角色，脱稿回答；把说不出的句子重新跟读，再延迟一段时间回忆。'),dict(minutes=60,title='纠错与巩固',instruction='重新进入不熟悉的对话。隔天回忆低于 80% 时减少新内容，不为赶数量跳过理解。')]
    else:
        recall_minutes=max(40,min(110,5*((review_rows+9)//10)))
        shadow_minutes=max(20,50-max(0,recall_minutes-40)//2)
        tasks=[dict(minutes=recall_minutes,title='间隔复习与拼读',instruction='打开下方近期、一周前和一个月前的对话，先回忆大意，再核对中文。第一周先用 20 分钟拼读韩文字母。复习量较大时优先处理忘记的内容，再学新课。'),dict(minutes=90,title='当天站内对话',instruction='按下方列表逐关学习。听一句、看整句中文，点不懂的词语看本句注释；确认谁在说、说给谁听。'),dict(minutes=shadow_minutes,title='正常语速跟读',instruction='模仿完整句子，再隐藏中文复述。0.8 倍速只用于辨音，最后回到正常速度。'),dict(minutes=240-recall_minutes-90-shadow_minutes,title='主动表达',instruction=months[month]['output'])]
    if day%30==0:
        exam=months[month]['examMinutes']
        tasks=[dict(minutes=exam,title='阶段检验',instruction=months[month]['checkpoint']),dict(minutes=240-exam,title='复盘与重学',instruction='核对客观题答案，把失分对应到站内词句，重新听读。作文分须经过实际批改，不能把估分当作实测。')]
    if day==170:
        tasks=[dict(minutes=180,title='完整限时检验',instruction=months[5]['checkpoint']),dict(minutes=60,title='复盘与重学',instruction='核对客观题、等待写作反馈，再复习站内对应词句。')]
    topic=' / '.join(dict.fromkeys(l['scene'] for l in assigned))
    if len(topic)>46:topic='当天情境对话与表达'
    days.append(dict(day=day,month=month+1,lessonId=(ids or review_ids)[0],lessonIds=ids,reviewLessonIds=review_ids,reviewGroups=groups,reviewRows=review_rows,topic=topic or '回忆、听写与表达',title='复习与检验' if review else '听懂、点词与回应',newWords=len(seen_words)-old_words,newSentences=len(seen_sentences)-old_sentences,cumulativeWords=len(seen_words),cumulativeSentences=len(seen_sentences),minutes=240,tasks=tasks))
for month in months:
    last=days[month['endDay']-1]
    month['words']=last['cumulativeWords'];month['sentences']=last['cumulativeSentences']
plan=dict(days=days,months=months,totalDays=180,dailyMinutes=240,totalHours=720,
 inventoryNote='对话文本按韩文去除空格和标点后去重；短回答和含多句的发言也各算一条，不等于同样数量的独立句型。词条包含词典原形、依存名词及基础表达。复习不增加数量；接触记录不等于掌握。',
 retentionRule='新对话安排隔天、一周后和一个月后再遇见；每五天还会整组复习前四天。下方复习列表可以直接进入。课程仍可自由选择，回忆不足 80% 时先补复习，再按自己的速度继续。最后一个月内容的后续复习会延续至第 210 天，云端学习与复习记录继续保留。',
 sources=[dict(label='国立国语院韩国语—汉语学习词典',url='https://krdict.korean.go.kr/chn'),dict(label='课程来源与审校覆盖',url='/content-sources.html'),dict(label='TOPIK 官方测评资料',url='https://www.topik.go.kr/')])
assert len(seen_words)>=6000 and len(seen_sentences)>=8000
assert sum(d['newWords'] for d in days)==len(seen_words)
assert sum(d['newSentences'] for d in days)==len(seen_sentences)
assert all(sum(t['minutes'] for t in d['tasks'])==240 for d in days)
assert all(d['newWords']==d['newSentences']==0 for d in days if d['day']%5==0)
(ROOT/'content/study-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
lines=['# 180 天站内韩语课程','',f"{len(course)} 关，{len(seen_words)} 个去重词条，{len(seen_sentences)} 条去重对话文本；每天四小时，共 720 小时。",'',plan['inventoryNote'],'']
for day in days:
    lines += [f"## 第 {day['day']} 天 · {day['title']}",'',f"新增 {day['newWords']} 词条 / {day['newSentences']} 句；累计 {day['cumulativeWords']} 词条 / {day['cumulativeSentences']} 句。",'']
    lines += [f"- {t['minutes']} 分钟：{t['title']}。{t['instruction']}" for t in day['tasks']]
    lines += ['','课程：'+', '.join(day['lessonIds'] or day['reviewLessonIds']),'']
    lines += ['复习：'+', '.join(day['reviewLessonIds']),'']
(ROOT/'docs/180-day-plan.md').write_text('\n'.join(lines).rstrip()+'\n')
print(json.dumps({'days':180,'lessons':len(course),'words':len(seen_words),'sentences':len(seen_sentences),'outsideContentCounted':False},ensure_ascii=False))
