"""Compile source-backed dialogue lessons; never substitute a schedule for content."""
import collections
import hashlib
import json
import math
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
CACHE = ROOT / '.sites-runtime/corpus'
JAMO = str.maketrans({'ᆫ':'ㄴ','ᆯ':'ㄹ','ᆷ':'ㅁ','ᆸ':'ㅂ','ᆼ':'ㅇ'})
TOPICS = {'인간':'人物与表达','삶':'生活与经历','식생활':'餐饮与生活','의생활':'穿着与购物',
          '주생활':'居住与环境','사회 생활':'社会与交往','경제 생활':'工作与经济',
          '교육':'校园与学习','종교':'文化与信仰','문화':'文化与休闲','자연':'自然与环境',
          '정치와 행정':'制度与公共事务','개념':'说明与表达'}
GRAMMAR = {
 'JKS':'主格助词，标记主语。','JKC':'补格助词，用在되다、아니다等前。','JKG':'属格助词，连接所属或修饰关系。',
 'JKO':'宾格助词，标记动作的对象。','JKV':'呼格助词，用来称呼对方。','JKQ':'引用助词，引出引用的内容。',
 'JC':'并列助词，连接名词。','JX':'辅助助词，增加话题、对比、限定等含义。',
 'JKB':'副词格助词，表示时间、地点、方向、方式等关系。',
 'EP':'先语末语尾，表达时态、敬语或语气。','EF':'终结语尾，表示句子的语气和礼貌程度。',
 'EC':'连接语尾，连接后面的动作、状态或辅助表达。','ETM':'冠形词形语尾，使前面的内容修饰名词。',
 'ETN':'名词形语尾，把动作或状态转成名词性表达。','VCP':'이다：表示“是”的判断形式。',
 'VCN':'아니다：表示“不是”的否定判断。','XSN':'名词后缀，构成派生名词。','XSV':'动词后缀，构成派生动词。',
 'XSA':'形容词后缀，构成派生形容词。','XPN':'前缀，为后面的词增加含义。','XR':'构词词根，与其他成分组成词。',
 'NNP':'专有名词，如人名、地名。','SN':'数字。','SL':'外语或字母。','SH':'汉字。','W_SERIAL':'序号。',
 'NNB':'依存名词，需要与前面的修饰成分一起理解。','MM':'冠形词，修饰后面的名词。',
 'VV':'动词词干；句中以语尾连接。','VA':'形容词词干；句中以语尾连接。','VX':'辅助用言，与前面的内容合用。',
 'MAG':'副词，修饰动作或状态。','MAJ':'连接副词。','NP':'代词。','NR':'数词。','IC':'感叹词或应答语。','NNG':'名词。'
}
SIMPLE = {
 ('는','JX'):'话题或对比助词。',('은','JX'):'话题或对比助词。',('도','JX'):'表示“也、连……也”。',
 ('만','JX'):'表示“只、仅”。',('부터','JX'):'表示起点：“从……起”。',('까지','JX'):'表示终点或范围：“到、直到、连……都”。',
 ('요','JX'):'增加礼貌语气。',('었','EP'):'过去或完成，常与词干缩合。',('았','EP'):'过去或完成，常与词干缩合。',
 ('였','EP'):'过去或完成，常与하다缩合。',('시','EP'):'主语敬语，尊敬动作或状态的主体。',
 ('으시','EP'):'主语敬语，尊敬动作或状态的主体。',('겠','EP'):'表示意愿、推测或礼貌委婉，结合整句判断。',
 ('하','XSV'):'하다：与前面的名词或词根组合成动词。',('하','XSA'):'하다：与前面的词根组合成形容词。',
 ('되','XSV'):'되다：与前面的词根组合，常表示成为、变化或被动。',
 ('들','XSN'):'复数后缀，表示多个对象。',('님','XSN'):'尊称后缀。',
 ('이','JKS'):'主格助词，标记主语。',('가','JKS'):'主格助词，标记主语。',
 ('을','JKO'):'宾格助词，标记动作对象。',('를','JKO'):'宾格助词，标记动作对象。',
 ('의','JKG'):'所属、关联或修饰，常对应“的”。',('에','JKB'):'格助词，表示时间、位置、去向、对象等；需结合整句理解。',
 ('에서','JKB'):'格助词，表示动作发生的地点或出发点。',('에게','JKB'):'格助词，表示动作所涉及的人：“给、对、向”等。',
 ('한테','JKB'):'口语格助词，表示动作所涉及的人：“给、对、向”等。',
 ('에게서','JKB'):'表示人的来源：“从某人那里”。',('한테서','JKB'):'口语中表示“从某人那里”。',
 ('보다','JKB'):'比较的基准：“比……”。',('처럼','JKB'):'表示相似：“像……一样”。',
 ('하고','JC'):'连接并列名词：“和”。',('와','JC'):'连接并列名词：“和”。',('과','JC'):'连接并列名词：“和”。'
}
SIMPLE.update({
 ('ㄴ','ETM'):'修饰后面的名词。形容词后表示当前性质；动词后通常表示已完成的动作或结果状态。',
 ('은','ETM'):'修饰后面的名词。形容词后表示当前性质；动词后通常表示已完成的动作或结果状态。',
 ('는','ETM'):'修饰后面的名词，通常表示正在进行、习惯性或现在的动作。',
 ('ㄹ','ETM'):'修饰后面的名词，表示预定、意向、推测或可能；具体含义取决于后接表达。',
 ('을','ETM'):'修饰后面的名词，表示预定、意向、推测或可能；具体含义取决于后接表达。',
 ('던','ETM'):'修饰后面的名词，回想过去持续、反复或尚未完成的情况。',
 ('예요','EF'):'礼貌判断语尾，用于名词后的“是……”表达。',
 ('ㄴ가요','EF'):'礼貌疑问语尾，委婉询问或确认。',
 ('다면서요','EF'):'引用所听到的陈述，再向对方确认：“听说……，是吗？”',
 ('ㄴ다면서요','EF'):'引用所听到的动作陈述，再向对方确认。',
 ('라면서요','EF'):'引用名词判断或转述，再向对方确认。',
 ('어서요','EF'):'用礼貌语气补充理由：“因为……”。',
 ('ㅂ시오','EF'):'正式敬语的请求或命令语尾；通常与시合成십시오。',
 ('잖니','EF'):'提醒听者双方已知的事实，带反问或确认语气：“不是……吗”。',
 ('이요','JX'):'用于名词性简短回答，增加礼貌语气。',
 ('ㄹ로','JKB'):'로/으로的口语缩合形式；뭘로相当于무엇으로，表示用什么、以什么等。',
 ('이서','JKS'):'接在人数表达后，表示这些人共同参与动作。',
 ('어야죠','EF'):'어야지요的缩合，表示“应该、必须”或确认应当如此。',
 ('랄까','EC'):'引用、推测表达的缩略；아니랄까 봐常表示“果然、不愧是”。',
 ('랄까','EF'):'라고 할까等的缩略，表示斟酌措辞：“该怎么说呢”。',
 ('던가요','EF'):'礼貌地询问过去经历或回想中的情况。',
 ('다는군요','EF'):'转述听到的陈述并表示新得知：“听说……啊”。',
 ('거늘','EC'):'较书面或古雅的连接语尾，表示背景、理由或转折。'
})


def audio(text):
    return '/audio/' + hashlib.sha256(text.encode()).hexdigest()[:20] + '.mp3'


def clean_gloss(sense):
    value = sense['zh']
    return (sense['definition'] if not value or '无对应' in value else value).replace('不知失措','不知所措')


def main():
    excluded = json.loads((ROOT / 'content/source-exclusions.json').read_text())
    selected = [d for d in json.loads((CACHE / 'selected-dialogues.json').read_text()) if d['id'] not in excluded]
    morphology = json.loads((CACHE / 'selected-morphology.json').read_text())
    dictionary = json.loads((CACHE / 'nikl-dictionary.json').read_text())
    byid, byterm = {}, collections.defaultdict(list)
    for e in dictionary:
        # Subentries (idioms) share the headword ID in this export. Keep the
        # lexical headword; never overwrite it with a later idiom definition.
        if e['id'] not in byid or (not byid[e['id']]['pos'] and e['pos']):
            byid[e['id']] = e
        byterm[e['term']].append(e)
    # Kiwi misread this contraction as 차다 + 어여. The source has passive
    # 차이다 + 어 (차여): stones being kicked while walking.
    stone = morphology['응. 걸을 때마다 돌멩이가 툭툭 차여.']
    for token in stone['tokens']:
        if token['start'] == 18 and token['tag'] == 'VV':
            token.update(form='차이', lemma='차이다', entryIds=['78220'])
        elif token['start'] == 18 and token['tag'] == 'EF':
            token.update(form='어', lemma='어')
    stone['words'].pop('차다', None)
    stone['words']['차이다'] = '78220'
    translations = {r['id']: r for r in map(json.loads, (CACHE / 'translations-plain.jsonl').read_text().splitlines())}
    review_path = CACHE / 'translations-reviewed.jsonl'
    reviewed = {r['id']: r for r in map(json.loads, review_path.read_text().splitlines())} if review_path.exists() else {}
    edits = json.loads((ROOT / 'content/editorial-overrides.json').read_text())
    for batch in sorted((ROOT / 'content/editorial-batches').glob('*.json')):
        for identity, text in json.loads(batch.read_text()).items():
            edits[identity] = {'translations':text}
    missing = [d['id'] for d in selected if d['id'] not in translations and d['id'] not in edits]
    assert not missing, f'Missing actual translations: {len(missing)} {missing[:8]}'
    foundation = json.loads((ROOT / 'content/foundation.json').read_text())
    review_log = [json.loads(r) for r in (ROOT / 'docs/editorial-review-log.jsonl').read_text().splitlines()]
    editorial_ids = {identity for row in review_log for identity in row['dialogueIds']}
    assert all(d['id'] in editorial_ids for d in selected), 'Unreviewed dialogue in release'
    grammar_misses = collections.Counter()

    def lexical_explanation(token, dialogue):
        term, tag = token['lemma'], token['tag']
        form = token['form'].translate(JAMO)
        if token.get('contextMeaning'):
            return term + '：' + token['contextMeaning']
        if (form, tag) in SIMPLE:
            return form + '：' + SIMPLE[(form, tag)]
        if tag.startswith('J'):
            entries = [e for e in byterm.get(form, []) if e['pos'] == '조사']
        elif tag.startswith('E'):
            lookups = ['-' + form + ('-' if tag == 'EP' else ''), '-' + form]
            entries = [e for lookup in dict.fromkeys(lookups) for e in byterm.get(lookup, []) if e['pos'] in {'어미','품사 없음'}]
        else:
            entries = [byid[i] for i in token['entryIds'] if i in byid]
            if not entries and tag == 'NNP':
                entries = byterm.get(term, [])
            wanted = {'VV':{'동사'},'VA':{'형용사'},'VX':{'보조 동사','보조 형용사'},
                      'NNG':{'명사'},'NP':{'대명사'},'NR':{'수사'},'NNB':{'의존 명사'},
                      'MM':{'관형사'},'MAG':{'부사'},'MAJ':{'부사'},'IC':{'감탄사'}}.get(tag)
            matching = [e for e in entries if wanted and e['pos'] in wanted]
            entries = matching or entries
        if entries:
            if term == dialogue['term']:
                return term + '：' + clean_gloss(dialogue)
            if tag.startswith(('J', 'E')):
                meanings = list(dict.fromkeys(s['definition'] for e in entries for s in e['senses']))
                cues = {'EF':('终结','句末'),'EC':('连接',),'ETM':('冠形','定语','修饰名词'),'ETN':('名词形','名词的功能')}.get(tag,())
                matching = [s for s in meanings if any(cue in s for cue in cues)]
                meanings = matching or meanings
            else:
                meanings = list(dict.fromkeys(clean_gloss(s) for e in entries for s in e['senses']))
            # The complete entry stays in the word card and source link. A
            # clickable sentence chunk should not dump dozens of senses.
            return (form if tag.startswith(('J', 'E')) else term) + '：' + '；'.join(meanings[:2]) + ('（还有其他词义，见词典）' if len(meanings)>2 else '')
        if tag in GRAMMAR:
            if tag.startswith(('E','J')):
                grammar_misses[(form, tag)] += 1
            return form + '：' + GRAMMAR[tag]
        if tag in {'SF','SP','SS','SSO','SSC','SE','SO','SW'}:
            return ''
        grammar_misses[(form, tag)] += 1
        return form + '：结合本句译文理解的构词成分。'

    course = foundation[:]
    all_review = []
    for d in selected:
        translated = edits.get(d['id'], reviewed.get(d['id'], translations.get(d['id'])))['translations']
        assert len(translated) == len(d['lines'])
        lines = []
        for n, (ko, zh) in enumerate(zip(d['lines'], translated)):
            analysis = morphology[ko]
            parts = []
            for span in re.finditer(r'\S+', ko):
                original = [t for t in analysis['tokens'] if span.start() <= t['start'] < span.end()]
                tokens = []
                for token in original:
                    token = dict(token)
                    if tokens and token['tag'] in {'XSV','XSA','XSN'}:
                        previous = tokens[-1]
                        candidate = previous['form'] + token['form'] + ('다' if token['tag'] in {'XSV','XSA'} else '')
                        wanted = {'XSV':'동사','XSA':'형용사','XSN':'명사'}[token['tag']]
                        matches = [e for e in byterm.get(candidate,[]) if e['pos']==wanted]
                        if matches and previous['tag'] in {'XR','NNG','NNP','MAG'}:
                            tokens.pop()
                            token = {**previous,'form':candidate,'lemma':candidate,
                                     'tag':{'XSV':'VV','XSA':'VA','XSN':'NNG'}[token['tag']],
                                     'entryIds':[e['id'] for e in matches]}
                    if token['tag']=='VX' and token['lemma']=='하다':
                        earlier = [t for t in analysis['tokens'] if t['start']<span.start()]
                        if earlier and earlier[-1]['form'] in {'어야','아야','여야'}:
                            token['contextMeaning']='与前面的 -아/어야 合用，表示“应该、必须”。'
                    tokens.append(token)
                explanations = list(dict.fromkeys(filter(None, (lexical_explanation(t, d) for t in tokens))))
                details = '；'.join(explanations) or '标点或停顿，按整句语调朗读。'
                stems = [t for t in tokens if t['tag'] in {'NNG','NNP','NP','NR','NNB','VV','VA','VX','MAG','MAJ','MM','IC'}]
                # A dictionary reference is explicitly labelled; it is not sold as
                # a machine-guessed context-specific gloss of an ambiguous word.
                meanings = list(dict.fromkeys(lexical_explanation(t, d) for t in stems))
                short = '；'.join(meanings) if meanings else details
                parts.append({'text':span.group(), 'meaning':'词义参考：' + short,
                              'explanation':details})
            words = []
            for term, eid in analysis['words'].items():
                entry = byid[d['entryId'] if term == d['term'] else eid]
                assert entry['term'] == term, (term, entry['term'], eid)
                if term == d['term']:
                    sense = next(s for s in entry['senses'] if s['id'] == d['senseId'])
                    word_zh, definition = clean_gloss(sense), sense['definition']
                else:
                    word_zh = '；'.join(dict.fromkeys(clean_gloss(s) for s in entry['senses']))
                    definition = '；'.join(dict.fromkeys(s['definition'] for s in entry['senses']))
                words.append({'id':hashlib.sha256(term.encode()).hexdigest()[:16], 'term':term,
                              'zh':word_zh, 'audio':audio(term), 'entryId':entry['id'],
                              'definition':definition, 'pronunciation':entry['pronunciation']})
            lines.append({'id':d['id'] + f'-{n+1}', 'ko':ko, 'zh':zh,
                          'note':f"本段关键词：{d['term']}（{clean_gloss(d)}）。点击词语可看原形、助词和语尾。",
                          'parts':parts, 'words':words, 'audio':audio(ko), 'speakerIndex':n % 2})
        course.append({'id':d['id'], 'stage':0, 'title':d['term'] + ' · ' + clean_gloss(d).split('；')[0].split('，')[0],
                       'scene':TOPICS.get(d['category'].split(' > ')[0], '情境对话'), 'roles':['说话人 A','说话人 B'],
                       'lines':lines, 'difficulty':d['difficulty'],
                       'source':{'url':f"https://krdict.korean.go.kr/chn/dicSearch/SearchView?ParaWordNo={d['entryId']}",
                                 'label':'国立国语院韩国语—汉语学习词典',
                                 'license':'https://creativecommons.org/licenses/by-sa/2.0/kr/'},
                       'sourceSenseId':d['senseId'], 'sourceLevel':d['level']})
        all_review.append({'id':d['id'], 'translationPasses':2,
                           'reviewMethod':'Complete Korean and Chinese read together by Codex AI editor',
                           'humanTeacherCertification':False,
                           'editorialCorrection':d['id'] in edits, 'sourceEntryId':d['entryId'], 'sourceSenseId':d['senseId']})
    added = course[len(foundation):]
    # 24 new-content days per month, six days of retrieval/review.
    sizes = [482, 582, 782, 682, 682, len(added)-3210]
    assert sum(sizes) == len(added) and min(sizes) > 0
    ordered, position = [], 0
    seen_words = set()
    def lesson_words(lesson):
        return {word['term'] for line in lesson['lines'] for word in line['words']}
    for month, count in enumerate(sizes):
        new_days = [month*30+i for i in range(1,31) if i % 5]
        pool = added[position:position+count]
        position += count
        bases = [l for l in foundation if l['stage'] == month]
        cursor = 0
        for i, day in enumerate(new_days):
            before = len(seen_words)
            remaining_words = set().union(*(lesson_words(l) for l in pool[cursor:]),
                                           *(lesson_words(l) for l in bases[math.ceil(i/4):]))
            target = math.ceil(len(remaining_words-seen_words)/(24-i))
            daily = []
            if i % 4 == 0:
                daily.append(bases[i//4])
                seen_words.update(lesson_words(daily[-1]))
            added_today = 0
            # Balance actual novel vocabulary, not just the number of lessons.
            # Keep source progression and leave at least one dialogue per day.
            while cursor < len(pool)-(23-i):
                if added_today and len(seen_words)-before >= target:
                    break
                daily.append(pool[cursor])
                seen_words.update(lesson_words(pool[cursor]))
                cursor += 1
                added_today += 1
            for lesson in daily:
                lesson['stage'], lesson['day'] = month, day
            ordered.extend(daily)
        assert cursor == len(pool)
    assert ordered[0]['id'] == 'c01'
    (CACHE / 'compiled-course.json').write_text(json.dumps(ordered,ensure_ascii=False,separators=(',',':'))+'\n')
    (ROOT / 'docs/curriculum-review-coverage.json').write_text(json.dumps(all_review,ensure_ascii=False,separators=(',',':'))+'\n')
    (CACHE / 'grammar-lookup-misses.json').write_text(json.dumps([{'form':f,'tag':t,'count':n} for (f,t),n in grammar_misses.most_common()],ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'lessons':len(ordered),'newDialogues':len(added),'grammarFallbacks':sum(grammar_misses.values()),'grammarFormsWithFallback':len(grammar_misses)},ensure_ascii=False))


if __name__ == '__main__':
    main()
