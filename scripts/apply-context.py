"""Assemble source-selected senses and authored grammar into clickable notes."""
import argparse
import hashlib
import json
import pathlib
import re
from contextual_senses import Lexicon,ROOT,CACHE,VERSION,TAGS,JAMO,load_selections
from context_grammar import grammar_note,number_meaning
from surface_readings import surface_reading

NAMES=json.loads((ROOT/'content/context-names.json').read_text())
READABLE_GLOSSES={('28818','1'):'韩国泡菜（辛奇）',('28026','1'):'旅行，旅游',('48655','1'):'硬币',('56548','1'):'听写',('57293','3'):'用餐、吃或喝（敬语）'}


def path(term):return '/audio/'+hashlib.sha256(term.encode()).hexdigest()[:20]+'.mp3'


def fallback_reading(part):
    """Names and grammar-only chunks can still be played on their own."""
    part['surfaceReading']=surface_reading(part['text'])
    text=part['text'].strip('.,?!\"\'“”‘’…')
    if not part['readings'] and text:
        part['readings']=[{'term':text,'audio':path(text)}]


def context_expression(lemma,tag,parts,index):
    before=parts[max(0,index-2):index]
    previous=before[-1]['tokens'] if before else []
    previous_forms={t['form'].translate(JAMO) for t in previous}
    prior_words={t['lemma'] for p in before for t in p['tokens']}
    if lemma in {'있다','없다'} and '수' in prior_words and any(t['tag']=='ETM' and t['form'].translate(JAMO) in {'ㄹ','을'} for p in before for t in p['tokens']):
        return ('能、可以（-ㄹ/을 수 있다）' if lemma=='있다' else '不能（-ㄹ/을 수 없다）')
    if lemma=='하다' and previous_forms&{'어야','아야','여야'}:
        return '应该、必须（与前面的 -아/어야 合用）'
    if lemma=='하다' and previous_forms&{'려고','으려고'}:
        return '打算做（-려고 하다）'
    if lemma=='하다' and previous_forms&{'ㄹ까','을까'}:
        return '考虑、打算做（-ㄹ/을까 하다）'
    if lemma=='되다' and previous_forms&{'어야','아야','여야'}:
        return '应该、必须（-아/어야 되다）'
    if lemma=='되다' and '게' in previous_forms and not any(t['lemma'] in {'어떻다'} for t in previous):
        return '变得、最终处于某种情况（-게 되다）'
    if lemma=='되다' and previous_forms&{'어도','아도','여도'}:
        return '可以、得到允许（-아/어도 되다）'
    if lemma=='보다' and tag=='VX':
        if previous_forms&{'나','ㄴ가','은가','는가','ᆫ가'}:return '看来、好像（根据情况推测）'
        if previous_forms&{'어','아','여'}:return '试着做（-아/어 보다）'
    if lemma=='주다' and tag=='VX' and previous_forms&{'어','아','여'}:
        return '为别人做某事（-아/어 주다）'
    if lemma=='드리다' and tag=='VX':
        return '为别人做某事（-아/어 드리다，谦敬表达）'
    if lemma=='나다' and tag=='VX' and '고' in previous_forms:
        return '做完前面的动作（-고 나다）'
    if lemma=='있다' and tag=='VX' and '고' in previous_forms:
        return '正在做、持续进行（-고 있다）'
    if lemma=='있다' and tag=='VX' and previous_forms&{'어','아','여'}:
        return '某种结果状态持续着（-아/어 있다）'
    if lemma=='말다' and tag=='VX':
        if '지' in previous_forms:return '不要做、停止做（-지 말다）'
        if '고' in previous_forms:return '结果还是、最终发生（-고 말다）'
    emotions={'화':'发火','짜증':'感到烦躁','신경질':'感到烦躁','겁':'害怕','용기':'鼓起勇气','흥미':'产生兴趣','호기심':'产生好奇心'}
    if lemma in {'나다','내다'} and tag=='VV':
        for noun,meaning in emotions.items():
            if noun in prior_words:
                if lemma=='내다' and noun in {'화','짜증','신경질'}:meaning='发脾气、表现出不满'
                return meaning+'（'+noun+('이/가 ' if lemma=='나다' else '을/를 ')+lemma+'）'
    if lemma=='여자' and index+1<len(parts) and any(t['lemma']=='친구' for t in parts[index+1]['tokens']):
        return '女性（여자 친구 合指“女朋友”）'
    if lemma=='남자' and index+1<len(parts) and any(t['lemma']=='친구' for t in parts[index+1]['tokens']):
        return '男性（남자 친구 合指“男朋友”）'
    return None


def construction_sense(item,parts,index):
    """Resolve a few grammatical constructions by explicit morphology.

    These are authored rules, not an inference that a model was correct.
    """
    lemma=item['lemma'];tokens=parts[index]['tokens']
    previous=parts[index-1]['tokens'] if index else []
    forms={t['form'].translate(JAMO) for t in previous}
    following=parts[index+1]['tokens'] if index+1<len(parts) else []
    if lemma=='수' and item['tag']=='NNB' and forms&{'ㄹ','을'} and any(t['lemma'] in {'있다','없다'} for t in following):return ('15615','1')
    if lemma=='있다' and item['tag']=='VX':
        if '고' in forms:return ('62595','2')
        if forms&{'어','아','여'}:return ('62595','3')
    if lemma=='주다' and item['tag']=='VX' and forms&{'어','아','여'}:return ('77245','1')
    if lemma=='드리다' and item['tag']=='VX':return ('59252','1')
    if lemma=='나다' and item['tag']=='VX' and '고' in forms:return ('62134','1')
    if lemma=='하다':
        if any(t['form'].translate(JAMO) in {'다고','ㄴ다고','는다고','라고'} and t['tag']=='EC' for t in tokens+previous):return ('73277','22')
        if forms & {'어야','아야','여야'}:return ('62888','4')
        if forms & {'려고','으려고'}:return ('62888','2')
        if forms & {'ㄹ까','을까'}:return ('73277','27')
    if lemma=='지다' and item['tag']=='VX':
        predicates=[t for t in tokens if t['tag'] in {'VA','VV'}]
        if predicates:return ('77247','3' if predicates[0]['tag']=='VA' else '2')
    if lemma=='친구' and any(t['lemma'] in {'여자','남자'} for t in previous):return ('29742','1')
    prior=parts[max(0,index-2):index]
    if lemma in {'있다','없다'} and any(t['lemma']=='수' for p in prior for t in p['tokens']) and any(t['tag']=='ETM' and t['form'].translate(JAMO) in {'ㄹ','을'} for p in prior for t in p['tokens']):
        return ('68797','5') if lemma=='있다' else ('89917','11')
    if lemma=='나다' and any(t['lemma'] in {'화','짜증','신경질','겁','용기','흥미','호기심'} for p in prior for t in p['tokens']):return ('62210','12')
    if lemma=='내다' and any(t['lemma'] in {'화','짜증','신경질','겁','용기','흥미','호기심'} for p in prior for t in p['tokens']):return ('89906','13')
    return None


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--partial',action='store_true');args=parser.parse_args()
    course=json.loads((CACHE/'compiled-course.json').read_text())
    selections=load_selections()
    editorial_path=ROOT/'content/context-editorial.json'
    editorial=json.loads(editorial_path.read_text()) if editorial_path.exists() else {}
    lexicon=Lexicon();issues=[];coverage=[];unknown_names=set();required=set()
    for lesson in course:
        if lesson['id'].startswith('c'):
            for line in lesson['lines']:
                for part in line['parts']:
                    chunks=part['explanation'].split('；')
                    matches=[w for w in line['words'] if any(re.search(r'(?<![가-힣])'+re.escape(w['term'])+r'(?![가-힣])',chunk.split('：')[0]) for chunk in chunks) or part['text'].strip('.?!')==w['term']]
                    part['readings']=[{'term':w['term'],'audio':w['audio']} for w in matches]
                    fallback_reading(part)
            continue
        prepared=lexicon.prepare(lesson);record=selections.get(lesson['id'])
        if not record or record['signature']!=prepared['signature']:
            issues.append({'id':lesson['id'],'type':'missing current sense selection'})
            if args.partial:continue
            continue
        lesson_rows=[]
        # The dialogue belongs to this exact source sense. When its headword
        # occurs once, that occurrence has authoritative sense evidence. With
        # multiple occurrences, keep contextual selection for each occurrence.
        source_id=lesson['id'].split('-')[0][1:]
        source_sense=lesson['sourceSenseId']
        source_term=lexicon.byid[source_id]['term']
        occurrences=[(i,j,k) for i,row in enumerate(prepared['parts']) for j,part in enumerate(row) for k,item in enumerate(part['items']) if item['lemma']==source_term]
        unique_target=occurrences[0] if len(occurrences)==1 else None
        for i,(line,parts) in enumerate(zip(lesson['lines'],prepared['parts'])):
            new_parts=[];line_words={}
            line_edits=editorial.get(line['id'],{})
            for j,part in enumerate(parts):
                glosses=[];lexical=[];readings=[];sources=[]
                edit=line_edits.get('parts',{}).get(str(j),{})
                for k,item in enumerate(part['items']):
                    choice_key=f'{i}_{j}_{k}'
                    root=edit.get('root') if k==edit.get('rootItem',0) else None
                    chosen=edit.get('choices',{}).get(str(k),record['choices'].get(choice_key,0))
                    if isinstance(chosen,dict):
                        chosen=next((ci for ci,candidate in enumerate(item['candidates']) if candidate['entryId']==chosen['entryId'] and candidate['senseId']==chosen['senseId']),-1)
                    construction=construction_sense(item,parts,j)
                    source_target=(i,j,k)==unique_target
                    if source_target and not root and str(k) not in edit.get('choices',{}):
                        chosen=next((ci for ci,candidate in enumerate(item['candidates']) if (candidate['entryId'],candidate['senseId'])==(source_id,source_sense)),chosen)
                    elif construction and not root and str(k) not in edit.get('choices',{}):
                        chosen=next((ci for ci,candidate in enumerate(item['candidates']) if (candidate['entryId'],candidate['senseId'])==construction),chosen)
                    if chosen<0 and not root:
                        issues.append({'id':lesson['id'],'line':i,'part':j,'item':k,'type':'no matching sense','ko':line['ko'],'lemma':item['lemma']})
                        continue
                    sense=item['candidates'][max(0,chosen)]
                    if root:
                        target=root;e=lexicon.byid[target['entryId']];s=next(s for s in e['senses'] if s['id']==target['senseId'])
                        sense={'lemma':e['term'],'entryId':e['id'],'senseId':s['id'],'meaning':s['zh'],'definition':s['definition'],'pos':e['pos']}
                    lemma=sense['lemma'];entry=lexicon.byid[sense['entryId']]
                    expression=context_expression(lemma,item['tag'],parts,j)
                    # A model may confuse a lexical verb with a homonymous
                    # auxiliary. Morphology is a review trigger, not a verdict:
                    # genuine auxiliaries can be retained by an authored choice.
                    if item['tag'] in {'VV','VA'} and entry['pos'].startswith('보조') and not (edit or expression or construction or source_target):
                        issues.append({'id':lesson['id'],'line':i,'part':j,'item':k,'type':'unreviewed lexical-to-auxiliary sense','ko':line['ko'],'lemma':lemma,'entryId':entry['id']})
                    edited_meaning=edit.get('lexicalMeaning') if k==edit.get('rootItem',0) else None
                    meaning=edited_meaning or expression or READABLE_GLOSSES.get((sense['entryId'],sense['senseId']),sense['meaning'])
                    lexical.append(lemma+'：'+meaning);glosses.append(meaning)
                    readings.append({'term':lemma,'audio':path(lemma)})
                    sources.append({'entryId':sense['entryId'],'senseId':sense['senseId'],'lemma':lemma,'origin':entry.get('origin','NIKL Korean-Chinese dictionary')})
                    word={'id':hashlib.sha256(lemma.encode()).hexdigest()[:16],'term':lemma,'zh':meaning,'audio':path(lemma),'entryId':sense['entryId'],'definition':(meaning if expression or edit.get('lexicalMeaning') else sense['definition']),'pronunciation':entry['pronunciation']}
                    if sense['entryId'].startswith('course:'):word.pop('entryId')
                    if lemma in line_words and meaning not in line_words[lemma]['zh']:
                        line_words[lemma]['zh']+='；'+meaning
                    else:line_words[lemma]=word
                    required.add(lemma)
                    lesson_rows.append({'key':choice_key,**sources[-1],'meaning':meaning,'mode':'authored context expression' if expression or edit else 'unique headword in source-sense example' if source_target else 'authored construction rule' if construction else entry.get('origin','selected NIKL sense')})
                grammar=[grammar_note(t,part['tokens']) for t in part['tokens']]
                grammar=list(dict.fromkeys(filter(None,grammar)))
                for t in part['tokens']:
                    if t['tag'] in TAGS and not any(item['lemma']==t['lemma'] for item in part['items']):
                        number=number_meaning(t['lemma']) if t['tag'] in {'NR','MM'} else None
                        if number:
                            lexical.append(t['lemma']+'：'+number);glosses.append(number)
                        else:issues.append({'id':lesson['id'],'line':i,'part':j,'type':'unmatched lexical item','lemma':t['lemma'],'text':part['text'],'ko':line['ko']})
                    if t['tag']=='NNP':
                        label=NAMES.get(t['lemma'])
                        if not label:
                            known=lexicon.byterm.get(t['lemma'],[])
                            label=known[0]['senses'][0]['zh'] if known else '专有名称：'+t['lemma']
                            unknown_names.add(t['lemma'])
                        lexical.append(t['lemma']+'：'+label);glosses.append(label)
                if not glosses:
                    number=number_meaning(part['text'])
                    if number:glosses.append(number);lexical.append(number)
                meaning=edit.get('meaning','；'.join(dict.fromkeys(glosses)) or '；'.join(grammar))
                explanation=edit.get('explanation','；'.join(lexical+grammar))
                if not meaning or not explanation:
                    issues.append({'id':lesson['id'],'line':i,'part':j,'type':'empty annotation','ko':line['ko'],'text':part['text']})
                new_part={'text':part['text'],'meaning':meaning,'explanation':explanation,'readings':list({r['term']:r for r in readings}.values()),'sources':sources}
                fallback_reading(new_part)
                new_parts.append(new_part)
            line['parts']=new_parts;line['words']=list(line_words.values())
            line['note']='点不懂的词，看本句词义、助词和语尾；听词语后，再听整句。'
            if line_edits.get('zh'):line['zh']=line_edits['zh']
            if line_edits.get('ko'):
                line['ko']=line_edits['ko']
                line['audio']=path(line['ko'])
        coverage.append({'id':lesson['id'],'signature':record['signature'],'method':VERSION,'items':lesson_rows})
    report={'dialoguesAssembled':len(coverage),'sourceSenseChoices':sum(len(r['items']) for r in coverage),'issues':issues,'properNamesToCheck':sorted(unknown_names),'teacherCertification':False}
    (CACHE/'context-assembly-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (CACHE/'context-sense-coverage.json').write_text(json.dumps(coverage,ensure_ascii=False,separators=(',',':'))+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in {'issues','properNamesToCheck'}}|{'issues':len(issues),'names':len(unknown_names)},ensure_ascii=False))
    if (issues or unknown_names) and not args.partial:
        raise SystemExit('Resolve editorial issues before release assembly.')
    (CACHE/'compiled-course.json').write_text(json.dumps(course,ensure_ascii=False,separators=(',',':'))+'\n')
    if not args.partial:
        published={'method':VERSION,'teacherCertification':False,'records':[{k:selections[l['id']][k] for k in ('id','signature','choices','model')} for l in course if not l['id'].startswith('c')]}
        (ROOT/'content/context-senses.json').write_text(json.dumps(published,ensure_ascii=False,separators=(',',':'))+'\n')
        (ROOT/'docs/context-annotation-coverage.json').write_text(json.dumps(coverage,ensure_ascii=False,separators=(',',':'))+'\n')
        (ROOT/'content/foundation.json').write_text(json.dumps([l for l in course if l['id'].startswith('c')],ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
